import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import CalendarMember, CalendarEventType, CalendarEvent
from ..schemas import EventCreate, EventBulkCreate, success, error
from ..services import add_audit_log, check_capacity, build_monthly_calendar

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/calendar/events")
def list_events(db: Session = Depends(get_db)):
    events = db.query(CalendarEvent).order_by(CalendarEvent.event_date.desc(), CalendarEvent.id.desc()).all()
    return success([{
        "id": e.id,
        "member_id": e.member_id,
        "member_name": e.member.display_name if e.member else None,
        "event_date": e.event_date.isoformat(),
        "event_type_id": e.event_type_id,
        "event_type_name": e.event_type.name if e.event_type else None,
        "title": e.title,
        "display_label": e.display_label,
        "is_archived": e.is_archived,
    } for e in events], "正式予定一覧を取得しました")

@router.post("/api/calendar/events")
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    member = db.get(CalendarMember, payload.member_id)
    if not member:
        return error("MEMBER_NOT_FOUND", "メンバーが見つかりません")
    
    # Check event_type existence only if provided
    event_type = None
    if payload.event_type_id:
        event_type = db.get(CalendarEventType, payload.event_type_id)
        if not event_type:
            return error("EVENT_TYPE_NOT_FOUND", "予定種類が見つかりません")
    
    # Set display_label to title if not provided
    if not payload.display_label:
        payload.display_label = payload.title
    
    # Check for duplicate events
    if payload.event_type_id:
        existing = db.query(CalendarEvent).filter(
            CalendarEvent.member_id == payload.member_id,
            CalendarEvent.event_date == payload.event_date,
            CalendarEvent.event_type_id == payload.event_type_id,
            CalendarEvent.is_archived == False,
        ).first()
        if existing:
            return error("DUPLICATE_EVENT", "同一メンバー・同日・同一予定種類の予定が既に存在します")
    else:
        existing = db.query(CalendarEvent).filter(
            CalendarEvent.member_id == payload.member_id,
            CalendarEvent.event_date == payload.event_date,
            CalendarEvent.title == payload.title,
            CalendarEvent.is_archived == False,
        ).first()
        if existing:
            return error("DUPLICATE_EVENT", "同一メンバー・同日・同一予定名の予定が既に存在します")
    
    # Capacity check if required and event_type is provided
    if event_type and event_type.requires_capacity_check and payload.event_date:
        capacity_check_result = check_capacity(db, payload.event_date, event_type.id)
        if not capacity_check_result["sufficient"]:
            return error("INSUFFICIENT_CAPACITY", "定員が不足しています", [{
                "error_code": "INSUFFICIENT_CAPACITY",
                "message": "定員が不足しています",
                "capacity_check": capacity_check_result,
            }], "定員ルールを確認してください")
    
    event = CalendarEvent(**payload.model_dump())
    db.add(event)
    db.flush()
    add_audit_log(db, "create_event", "calendar_event", event.id, request=payload.model_dump())
    db.commit()
    return success({"id": event.id}, "正式予定を作成しました")

@router.post("/api/calendar/events/{event_id}/archive")
def archive_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(CalendarEvent, event_id)
    if not event:
        return error("EVENT_NOT_FOUND", "予定が見つかりません")
    event.is_archived = True
    add_audit_log(db, "archive_event", "calendar_event", event.id)
    db.commit()
    return success({"id": event.id}, "予定をアーカイブしました")

@router.post("/api/calendar/events/bulk")
def create_events_bulk(payload: EventBulkCreate, db: Session = Depends(get_db)):
    success_count = 0
    error_count = 0
    errors = []
    created_ids = []

    for idx, event_data in enumerate(payload.events):
        try:
            # Resolve member_id from member_name if not provided
            member_id = event_data.member_id
            if member_id is None and event_data.member_name:
                member = db.query(CalendarMember).filter(
                    CalendarMember.display_name == event_data.member_name,
                    CalendarMember.is_active == True
                ).first()
                if not member:
                    errors.append({
                        "index": idx,
                        "error": "MEMBER_NOT_FOUND",
                        "message": f"メンバー名 '{event_data.member_name}' が見つかりません",
                        "data": event_data.model_dump()
                    })
                    error_count += 1
                    continue
                member_id = member.id
            elif member_id is None:
                errors.append({
                    "index": idx,
                    "error": "MEMBER_REQUIRED",
                    "message": "member_id または member_name のいずれかを指定してください",
                    "data": event_data.model_dump()
                })
                error_count += 1
                continue

            member = db.get(CalendarMember, member_id)
            if not member:
                errors.append({
                    "index": idx,
                    "error": "MEMBER_NOT_FOUND",
                    "message": f"メンバーID {member_id} が見つかりません",
                    "data": event_data.model_dump()
                })
                error_count += 1
                continue

            # Resolve event_type_id from event_type_name if not provided
            event_type_id = event_data.event_type_id
            event_type = None
            if event_type_id is None and event_data.event_type_name:
                event_type = db.query(CalendarEventType).filter(
                    CalendarEventType.name == event_data.event_type_name,
                    CalendarEventType.is_active == True
                ).first()
                if not event_type:
                    errors.append({
                        "index": idx,
                        "error": "EVENT_TYPE_NOT_FOUND",
                        "message": f"予定種類名 '{event_data.event_type_name}' が見つかりません",
                        "data": event_data.model_dump()
                    })
                    error_count += 1
                    continue
                event_type_id = event_type.id
            elif event_type_id is not None:
                event_type = db.get(CalendarEventType, event_type_id)
                if not event_type:
                    errors.append({
                        "index": idx,
                        "error": "EVENT_TYPE_NOT_FOUND",
                        "message": f"予定種類ID {event_type_id} が見つかりません",
                        "data": event_data.model_dump()
                    })
                    error_count += 1
                    continue

            # Set display_label to title if not provided
            if not event_data.display_label:
                event_data.display_label = event_data.title

            # Check for duplicate events
            if event_type_id:
                existing = db.query(CalendarEvent).filter(
                    CalendarEvent.member_id == member_id,
                    CalendarEvent.event_date == event_data.event_date,
                    CalendarEvent.event_type_id == event_type_id,
                    CalendarEvent.is_archived == False,
                ).first()
                if existing:
                    errors.append({
                        "index": idx,
                        "error": "DUPLICATE_EVENT",
                        "message": "同一メンバー・同日・同一予定種類の予定が既に存在します",
                        "data": event_data.model_dump()
                    })
                    error_count += 1
                    continue
            else:
                existing = db.query(CalendarEvent).filter(
                    CalendarEvent.member_id == member_id,
                    CalendarEvent.event_date == event_data.event_date,
                    CalendarEvent.title == event_data.title,
                    CalendarEvent.is_archived == False,
                ).first()
                if existing:
                    errors.append({
                        "index": idx,
                        "error": "DUPLICATE_EVENT",
                        "message": "同一メンバー・同日・同一予定名の予定が既に存在します",
                        "data": event_data.model_dump()
                    })
                    error_count += 1
                    continue

            # Capacity check if required and event_type is provided
            if event_type and event_type.requires_capacity_check and event_data.event_date:
                capacity_check_result = check_capacity(db, event_data.event_date, event_type.id)
                if not capacity_check_result["sufficient"]:
                    errors.append({
                        "index": idx,
                        "error": "INSUFFICIENT_CAPACITY",
                        "message": "定員が不足しています",
                        "data": event_data.model_dump(),
                        "capacity_check": capacity_check_result
                    })
                    error_count += 1
                    continue

            event = CalendarEvent(
                member_id=member_id,
                event_date=event_data.event_date,
                event_type_id=event_type_id,
                title=event_data.title,
                display_label=event_data.display_label,
                memo=event_data.memo,
                source_type=event_data.source_type
            )
            db.add(event)
            db.flush()
            add_audit_log(db, "create_event_bulk", "calendar_event", event.id, request=event_data.model_dump())
            created_ids.append(event.id)
            success_count += 1

        except Exception as e:
            errors.append({
                "index": idx,
                "error": "INTERNAL_ERROR",
                "message": str(e),
                "data": event_data.model_dump()
            })
            error_count += 1

    db.commit()

    return success({
        "success_count": success_count,
        "error_count": error_count,
        "created_ids": created_ids,
        "errors": errors
    }, f"バルクインポート完了: 成功 {success_count}件, 失敗 {error_count}件")

@router.get("/api/calendar/events/monthly")
def monthly_events(year: int, month: int, department_id: int | None = None, db: Session = Depends(get_db)):
    if month < 1 or month > 12:
        return error("INVALID_MONTH", "monthは1〜12で指定してください")
    data = build_monthly_calendar(db, year, month, department_id)
    return success(data, "月間予定を取得しました")
