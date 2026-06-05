import json
import logging
from calendar import monthrange
from datetime import date, datetime
from sqlalchemy.orm import Session
from .models import CalendarMember, CalendarEventType, CalendarEventDraft, CalendarEvent, AuditLog, Department, CalendarMemberDepartment, CalendarEventTypeCapacityRule, Studio, Program, ProgramSchedule, HistoryEvent, HistoryAggregation

logger = logging.getLogger(__name__)

def add_audit_log(db: Session, action: str, target_type: str, target_id: int | None, request=None, response=None, actor_name="system"):
    log = AuditLog(
        actor_type="system",
        actor_name=actor_name,
        action=action,
        target_type=target_type,
        target_id=target_id,
        request_json=json.dumps(request, ensure_ascii=False, default=str) if request is not None else None,
        response_json=json.dumps(response, ensure_ascii=False, default=str) if response is not None else None,
    )
    db.add(log)

def validate_draft(db: Session, draft: CalendarEventDraft) -> dict:
    details = []

    member = None
    if draft.member_id:
        member = db.get(CalendarMember, draft.member_id)
    elif draft.member_name_raw:
        member = db.query(CalendarMember).filter(CalendarMember.display_name == draft.member_name_raw, CalendarMember.is_active == True).first()
        if member:
            draft.member_id = member.id

    if not member or not member.is_active:
        details.append({
            "error_code": "MEMBER_NOT_FOUND",
            "message": "メンバーが見つかりません",
            "value": draft.member_name_raw or draft.member_id,
        })

    event_type = None
    if draft.event_type_id:
        event_type = db.get(CalendarEventType, draft.event_type_id)
    elif draft.event_type_name_raw:
        event_type = db.query(CalendarEventType).filter(CalendarEventType.name == draft.event_type_name_raw, CalendarEventType.is_active == True).first()
        if not event_type:
            event_type = db.query(CalendarEventType).filter(CalendarEventType.short_label == draft.event_type_name_raw, CalendarEventType.is_active == True).first()
        if event_type:
            draft.event_type_id = event_type.id

    # Only check event_type existence if event_type_id is provided
    if draft.event_type_id and (not event_type or not event_type.is_active):
        details.append({
            "error_code": "EVENT_TYPE_NOT_FOUND",
            "message": "予定種類が見つかりません",
            "value": draft.event_type_name_raw or draft.event_type_id,
        })

    # Check for duplicates
    if draft.member_id:
        if draft.event_type_id:
            duplicated = db.query(CalendarEvent).filter(
                CalendarEvent.member_id == draft.member_id,
                CalendarEvent.event_date == draft.event_date,
                CalendarEvent.event_type_id == draft.event_type_id,
                CalendarEvent.is_archived == False,
            ).first()
            if duplicated:
                details.append({
                    "error_code": "DUPLICATE_EVENT",
                    "message": "同じメンバー・同じ日・同じ予定種類の正式予定が既にあります",
                    "event_id": duplicated.id,
                })
        else:
            # Use title for duplicate check when event_type_id is null
            if draft.title:
                duplicated = db.query(CalendarEvent).filter(
                    CalendarEvent.member_id == draft.member_id,
                    CalendarEvent.event_date == draft.event_date,
                    CalendarEvent.title == draft.title,
                    CalendarEvent.is_archived == False,
                ).first()
                if duplicated:
                    details.append({
                        "error_code": "DUPLICATE_EVENT",
                        "message": "同じメンバー・同じ日・同じ予定名の正式予定が既にあります",
                        "event_id": duplicated.id,
                    })

    capacity_check_result = None
    # Only check capacity if event_type is provided and requires it
    if event_type and event_type.requires_capacity_check and draft.event_date:
        capacity_check_result = check_capacity(db, draft.event_date, event_type.id)
        if not capacity_check_result["sufficient"]:
            details.append({
                "error_code": "INSUFFICIENT_CAPACITY",
                "message": "定員が不足しています",
                "capacity_check": capacity_check_result,
            })

    if details:
        draft.validation_status = "error"
        return {
            "valid": False,
            "details": details,
            "suggestion": "メンバー名、予定種類、日付、重複予定を確認してください。",
            "capacity_check": capacity_check_result,
        }

    draft.validation_status = "valid"
    return {
        "valid": True,
        "details": [],
        "suggestion": "",
        "capacity_check": capacity_check_result,
    }

def check_capacity(db: Session, event_date: date, event_type_id: int) -> dict:
    dt = event_date
    is_weekend = dt.weekday() >= 5
    day_type = "weekend" if is_weekend else "weekday"
    
    rules = db.query(CalendarEventTypeCapacityRule).filter(
        CalendarEventTypeCapacityRule.event_type_id == event_type_id,
        CalendarEventTypeCapacityRule.is_active == True,
    ).all()
    
    applicable_rules = []
    for rule in rules:
        if rule.day_type == "all" or rule.day_type == day_type:
            applicable_rules.append(rule)
    
    if not applicable_rules:
        return {
            "sufficient": True,
            "required": 0,
            "current": 0,
            "message": "定員ルールなし",
        }
    
    total_required = sum(r.required_count for r in applicable_rules)
    
    existing_events = db.query(CalendarEvent).filter(
        CalendarEvent.event_date == event_date,
        CalendarEvent.event_type_id == event_type_id,
        CalendarEvent.is_archived == False,
    ).all()
    
    current_count = len(existing_events)
    
    sufficient = current_count >= total_required
    
    return {
        "sufficient": sufficient,
        "required": total_required,
        "current": current_count,
        "message": f"必要: {total_required}, 現在: {current_count}",
    }

def approve_draft(db: Session, draft: CalendarEventDraft) -> CalendarEvent:
    result = validate_draft(db, draft)
    if not result["valid"]:
        raise ValueError(json.dumps(result, ensure_ascii=False))

    event = CalendarEvent(
        member_id=draft.member_id,
        event_date=draft.event_date,
        event_type_id=draft.event_type_id,
        title=draft.title,
        display_label=draft.display_label or draft.title,
        memo=draft.memo,
        source_type=draft.source_type,
        approval_status="approved",
    )
    db.add(event)
    db.flush()

    draft.approval_status = "approved"
    add_audit_log(db, "approve_draft", "calendar_event_draft", draft.id, response={"event_id": event.id})
    logger.info("draft approved: draft_id=%s event_id=%s", draft.id, event.id)
    return event

def build_monthly_calendar(db: Session, year: int, month: int, department_id: int | None = None) -> dict:
    last_day = monthrange(year, month)[1]
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]

    days = []
    for d in range(1, last_day + 1):
        dt = date(year, month, d)
        days.append({
            "date": dt.isoformat(),
            "day": d,
            "weekday": weekdays[dt.weekday()],
            "is_weekend": dt.weekday() >= 5,
        })

    members_query = db.query(CalendarMember).filter(CalendarMember.is_active == True)
    if department_id:
        member_ids_with_dept = db.query(CalendarMemberDepartment.member_id).filter(
            CalendarMemberDepartment.department_id == department_id
        ).all()
        member_ids = [m[0] for m in member_ids_with_dept]
        if member_ids:
            members_query = members_query.filter(CalendarMember.id.in_(member_ids))
        else:
            members_query = members_query.filter(False)
    members = members_query.order_by(CalendarMember.display_order, CalendarMember.id).all()

    events = db.query(CalendarEvent).filter(
        CalendarEvent.event_date >= date(year, month, 1),
        CalendarEvent.event_date <= date(year, month, last_day),
        CalendarEvent.is_archived == False,
    ).all()

    by_member_date = {}
    for event in events:
        key = (event.member_id, event.event_date.isoformat())
        by_member_date.setdefault(key, []).append({
            "id": event.id,
            "member_id": event.member_id,
            "event_date": event.event_date.isoformat(),
            "event_type_id": event.event_type_id,
            "title": event.title,
            "display_label": event.display_label or event.title,
            "memo": event.memo or "",
            "display_color": event.event_type.display_color if event.event_type else "#e5e7eb",
            "display_symbol": event.event_type.display_symbol if event.event_type else None,
        })

    member_rows = []
    for member in members:
        events_by_date = {}
        for day in days:
            events_by_date[day["date"]] = by_member_date.get((member.id, day["date"]), [])
        member_rows.append({
            "member_id": member.id,
            "display_name": member.display_name,
            "short_name": member.short_name,
            "events_by_date": events_by_date,
        })

    capacity_info = {}
    event_types_with_rules = db.query(CalendarEventType).filter(
        CalendarEventType.id.in_(
            db.query(CalendarEventTypeCapacityRule.event_type_id).filter(
                CalendarEventTypeCapacityRule.is_active == True
            ).distinct()
        ),
        CalendarEventType.is_active == True
    ).all()
    
    for day in days:
        dt = date.fromisoformat(day["date"])
        day_capacity = {}
        for et in event_types_with_rules:
            check_result = check_capacity(db, dt, et.id)
            day_capacity[et.id] = {
                "event_type_name": et.name,
                "sufficient": check_result["sufficient"],
                "required": check_result["required"],
                "current": check_result["current"],
                "message": check_result["message"],
            }
        capacity_info[day["date"]] = day_capacity

    studios = db.query(Studio).filter(Studio.is_active == True).order_by(Studio.display_order, Studio.id).all()
    
    program_schedules = db.query(ProgramSchedule).filter(
        ProgramSchedule.event_date >= date(year, month, 1),
        ProgramSchedule.event_date <= date(year, month, last_day),
    ).all()
    
    by_studio_date = {}
    for schedule in program_schedules:
        key = (schedule.studio_id, schedule.event_date.isoformat())
        by_studio_date.setdefault(key, []).append({
            "schedule_id": schedule.id,
            "program_id": schedule.program_id,
            "studio_id": schedule.studio_id,
            "event_date": schedule.event_date.isoformat(),
            "program_name": schedule.program.name if schedule.program else None,
            "program_short_label": schedule.program.short_label if schedule.program else None,
            "program_display_color": schedule.program.display_color if schedule.program else None,
        })
    
    studio_rows = []
    for studio in studios:
        programs_by_date = {}
        for day in days:
            programs_by_date[day["date"]] = by_studio_date.get((studio.id, day["date"]), [])
        studio_rows.append({
            "studio_id": studio.id,
            "studio_name": studio.name,
            "studio_code": studio.code,
            "programs_by_date": programs_by_date,
        })

    return {
        "year": year,
        "month": month,
        "days": days,
        "members": member_rows,
        "capacity_info": capacity_info,
        "studios": studio_rows,
    }

def archive_old_events(db: Session, cutoff_date: date | None = None) -> dict:
    """
    Move events older than 1 month to history_events table.
    Also update history_aggregations table.
    """
    from dateutil.relativedelta import relativedelta

    if cutoff_date is None:
        # Archive events from before the previous month (keep current and previous month in calendar_events)
        cutoff_date = (date.today().replace(day=1) - relativedelta(months=1))

    # Find events to archive
    events_to_archive = db.query(CalendarEvent).filter(
        CalendarEvent.event_date < cutoff_date,
        CalendarEvent.is_archived == False,
    ).all()

    archived_count = 0
    for event in events_to_archive:
        # Get member's primary department
        department_id = None
        department_name = None
        if event.member:
            primary_dept = db.query(CalendarMemberDepartment).filter(
                CalendarMemberDepartment.member_id == event.member_id
            ).first()
            if primary_dept:
                department_id = primary_dept.department_id
                department_name = primary_dept.department.name if primary_dept.department else None

        # Create history event
        history_event = HistoryEvent(
            member_id=event.member_id,
            member_display_name=event.member.display_name if event.member else "Unknown",
            department_id=department_id,
            department_name=department_name,
            event_date=event.event_date,
            event_type_id=event.event_type_id,
            event_type_name=event.event_type.name if event.event_type else None,
            event_type_code=event.event_type.code if event.event_type else None,
            title=event.title,
            display_label=event.display_label,
            memo=event.memo,
            source_type=event.source_type,
            source_detail=event.source_detail,
            original_event_id=event.id,
            created_at=event.created_at,
        )
        db.add(history_event)

        # Mark original event as archived
        event.is_archived = True
        archived_count += 1

    db.flush()

    # Update aggregations
    update_history_aggregations(db)

    db.commit()

    logger.info("archived %d events to history_events", archived_count)
    return {
        "archived_count": archived_count,
        "cutoff_date": cutoff_date.isoformat(),
    }

def update_history_aggregations(db: Session) -> dict:
    """
    Update history_aggregations table based on history_events.
    This is used by AI for analysis.
    """
    # Clear existing aggregations (simple approach)
    db.query(HistoryAggregation).delete()

    # Rebuild aggregations from history_events
    from sqlalchemy import func

    aggregations = db.query(
        HistoryEvent.member_id,
        HistoryEvent.member_display_name,
        HistoryEvent.department_id,
        HistoryEvent.department_name,
        func.extract('year', HistoryEvent.event_date).label('year'),
        func.extract('month', HistoryEvent.event_date).label('month'),
        HistoryEvent.event_type_id,
        HistoryEvent.event_type_name,
        HistoryEvent.event_type_code,
        func.count(HistoryEvent.id).label('count')
    ).group_by(
        HistoryEvent.member_id,
        HistoryEvent.member_display_name,
        HistoryEvent.department_id,
        HistoryEvent.department_name,
        func.extract('year', HistoryEvent.event_date),
        func.extract('month', HistoryEvent.event_date),
        HistoryEvent.event_type_id,
        HistoryEvent.event_type_name,
        HistoryEvent.event_type_code,
    ).all()

    created_count = 0
    for agg in aggregations:
        aggregation = HistoryAggregation(
            member_id=agg.member_id,
            member_display_name=agg.member_display_name,
            department_id=agg.department_id,
            department_name=agg.department_name,
            year=int(agg.year),
            month=int(agg.month),
            event_type_id=agg.event_type_id,
            event_type_name=agg.event_type_name,
            event_type_code=agg.event_type_code,
            count=int(agg.count),
        )
        db.add(aggregation)
        created_count += 1

    db.commit()

    logger.info("updated %d history_aggregations", created_count)
    return {
        "created_count": created_count,
    }

def archive_old_program_schedules(db: Session, cutoff_date: date | None = None) -> dict:
    """
    Move program schedules older than 1 month to program_history_events table.
    Also update program_history_aggregations table.
    """
    from dateutil.relativedelta import relativedelta

    if cutoff_date is None:
        cutoff_date = date.today() - relativedelta(months=1)

    # Find program schedules to archive
    schedules_to_archive = db.query(ProgramSchedule).filter(
        ProgramSchedule.event_date < cutoff_date
    ).all()

    archived_count = 0
    for schedule in schedules_to_archive:
        # Create program history event
        program_history_event = ProgramHistoryEvent(
            program_id=schedule.program_id,
            program_name=schedule.program.name if schedule.program else "Unknown",
            studio_id=schedule.studio_id,
            studio_name=schedule.studio.name if schedule.studio else "Unknown",
            event_date=schedule.event_date,
        )
        db.add(program_history_event)

        # Delete original schedule
        db.delete(schedule)
        archived_count += 1

    db.commit()

    logger.info("archived %d program schedules", archived_count)

    # Update aggregations
    update_program_history_aggregations(db)

    return {
        "archived_count": archived_count,
    }

def update_program_history_aggregations(db: Session) -> dict:
    """
    Update program_history_aggregations table based on program_history_events.
    This is used by AI for analysis.
    """
    # Clear existing aggregations (simple approach)
    db.query(ProgramHistoryAggregation).delete()

    # Rebuild aggregations from program_history_events
    from sqlalchemy import func

    aggregations = db.query(
        ProgramHistoryEvent.program_id,
        ProgramHistoryEvent.program_name,
        ProgramHistoryEvent.studio_id,
        ProgramHistoryEvent.studio_name,
        func.extract('year', ProgramHistoryEvent.event_date).label('year'),
        func.extract('month', ProgramHistoryEvent.event_date).label('month'),
        func.count(ProgramHistoryEvent.id).label('count')
    ).group_by(
        ProgramHistoryEvent.program_id,
        ProgramHistoryEvent.program_name,
        ProgramHistoryEvent.studio_id,
        ProgramHistoryEvent.studio_name,
        func.extract('year', ProgramHistoryEvent.event_date),
        func.extract('month', ProgramHistoryEvent.event_date),
    ).all()

    created_count = 0
    for agg in aggregations:
        aggregation = ProgramHistoryAggregation(
            program_id=agg.program_id,
            program_name=agg.program_name,
            studio_id=agg.studio_id,
            studio_name=agg.studio_name,
            year=int(agg.year),
            month=int(agg.month),
            count=int(agg.count),
        )
        db.add(aggregation)
        created_count += 1

    db.commit()

    logger.info("updated %d program_history_aggregations", created_count)
    return {
        "created_count": created_count,
    }
