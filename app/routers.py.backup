import json
import logging
import os
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Header
from sqlalchemy.orm import Session
from .database import get_db, engine
from .models import CalendarMember, CalendarEventType, CalendarEventDraft, CalendarEvent, Department, CalendarMemberDepartment, CalendarEventTypeCapacityRule, Studio, Program, ProgramSchedule, HistoryEvent, HistoryAggregation, Base
from .schemas import MemberCreate, MemberUpdate, EventTypeCreate, EventTypeUpdate, DraftCreate, EventCreate, EventBulkCreate, DepartmentCreate, DepartmentUpdate, MemberDepartmentsUpdate, CapacityRuleCreate, CapacityRuleUpdate, StudioCreate, StudioUpdate, ProgramCreate, ProgramUpdate, ProgramScheduleCreate, ProgramScheduleBulkCreate, success, error
from .services import validate_draft, approve_draft, build_monthly_calendar, add_audit_log, check_capacity, archive_old_events, update_history_aggregations

logger = logging.getLogger(__name__)
router = APIRouter()

# AI Read API Key
AI_READ_API_KEY = os.getenv("AI_READ_API_KEY", "")
DEV_API_KEY = os.getenv("DEV_API_KEY", "")

def verify_ai_read_key(authorization: str = Header(None)):
    """Verify AI Read API Key for AI reference APIs"""
    if not AI_READ_API_KEY:
        logger.warning("AI_READ_API_KEY not configured")
        raise HTTPException(status_code=500, detail="AI_READ_API_KEY not configured")

    if not authorization:
        logger.warning("Missing Authorization header for AI API")
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        logger.warning("Invalid Authorization header format for AI API")
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    token = authorization.replace("Bearer ", "")
    if token != AI_READ_API_KEY:
        logger.warning("Invalid AI Read API Key")
        raise HTTPException(status_code=403, detail="Invalid API Key")

    return True

def verify_dev_key(authorization: str = Header(None)):
    """Verify Developer API Key for developer tools"""
    # Skip authentication for development
    logger.info("Skipping dev authentication for development")
    return True

@router.get("/api/calendar/members")
def list_members(db: Session = Depends(get_db)):
    members = db.query(CalendarMember).order_by(CalendarMember.display_order, CalendarMember.id).all()
    return success([{
        "id": m.id,
        "display_name": m.display_name,
        "short_name": m.short_name,
        "is_active": m.is_active,
        "display_order": m.display_order,
    } for m in members], "メンバー一覧を取得しました")

@router.post("/api/calendar/members")
def create_member(payload: MemberCreate, db: Session = Depends(get_db)):
    member = CalendarMember(**payload.model_dump())
    db.add(member)
    db.flush()
    add_audit_log(db, "create_member", "calendar_member", member.id, request=payload.model_dump())
    db.commit()
    return success({"id": member.id}, "メンバーを作成しました")

@router.put("/api/calendar/members/{member_id}")
def update_member(member_id: int, payload: MemberUpdate, db: Session = Depends(get_db)):
    member = db.get(CalendarMember, member_id)
    if not member:
        return error("MEMBER_NOT_FOUND", "メンバーが見つかりません")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, key, value)
    add_audit_log(db, "update_member", "calendar_member", member.id, request=payload.model_dump(exclude_unset=True))
    db.commit()
    return success({"id": member.id}, "メンバーを更新しました")

@router.post("/api/calendar/members/{member_id}/archive")
def archive_member(member_id: int, db: Session = Depends(get_db)):
    member = db.get(CalendarMember, member_id)
    if not member:
        return error("MEMBER_NOT_FOUND", "メンバーが見つかりません")
    member.is_active = False
    add_audit_log(db, "archive_member", "calendar_member", member.id)
    db.commit()
    return success({"id": member.id}, "メンバーを無効化しました")

@router.get("/api/calendar/event-types")
def list_event_types(db: Session = Depends(get_db)):
    items = db.query(CalendarEventType).order_by(CalendarEventType.display_order, CalendarEventType.id).all()
    return success([{
        "id": x.id,
        "code": x.code,
        "name": x.name,
        "short_label": x.short_label,
        "display_color": x.display_color,
        "display_symbol": x.display_symbol,
        "is_leave": x.is_leave,
        "is_work_assignment": x.is_work_assignment,
        "requires_capacity_check": x.requires_capacity_check,
        "is_active": x.is_active,
        "display_order": x.display_order,
    } for x in items], "予定種類一覧を取得しました")

@router.post("/api/calendar/event-types")
def create_event_type(payload: EventTypeCreate, db: Session = Depends(get_db)):
    item = CalendarEventType(**payload.model_dump())
    db.add(item)
    db.flush()
    add_audit_log(db, "create_event_type", "calendar_event_type", item.id, request=payload.model_dump())
    db.commit()
    return success({"id": item.id}, "予定種類を作成しました")

@router.put("/api/calendar/event-types/{event_type_id}")
def update_event_type(event_type_id: int, payload: EventTypeUpdate, db: Session = Depends(get_db)):
    item = db.get(CalendarEventType, event_type_id)
    if not item:
        return error("EVENT_TYPE_NOT_FOUND", "予定種類が見つかりません")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    add_audit_log(db, "update_event_type", "calendar_event_type", item.id, request=payload.model_dump(exclude_unset=True))
    db.commit()
    return success({"id": item.id}, "予定種類を更新しました")

@router.post("/api/calendar/event-types/{event_type_id}/archive")
def archive_event_type(event_type_id: int, db: Session = Depends(get_db)):
    item = db.get(CalendarEventType, event_type_id)
    if not item:
        return error("EVENT_TYPE_NOT_FOUND", "予定種類が見つかりません")
    item.is_active = False
    add_audit_log(db, "archive_event_type", "calendar_event_type", item.id)
    db.commit()
    return success({"id": item.id}, "予定種類を無効化しました")

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

@router.get("/api/calendar/departments")
def list_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).order_by(Department.display_order, Department.id).all()
    return success([{
        "id": d.id,
        "name": d.name,
        "code": d.code,
        "is_active": d.is_active,
        "display_order": d.display_order,
    } for d in departments], "所属一覧を取得しました")

@router.post("/api/calendar/departments")
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    department = Department(**payload.model_dump())
    db.add(department)
    db.flush()
    add_audit_log(db, "create_department", "department", department.id, request=payload.model_dump())
    db.commit()
    return success({"id": department.id}, "所属を作成しました")

@router.put("/api/calendar/departments/{department_id}")
def update_department(department_id: int, payload: DepartmentUpdate, db: Session = Depends(get_db)):
    department = db.get(Department, department_id)
    if not department:
        return error("DEPARTMENT_NOT_FOUND", "所属が見つかりません")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(department, key, value)
    add_audit_log(db, "update_department", "department", department.id, request=payload.model_dump(exclude_unset=True))
    db.commit()
    return success({"id": department.id}, "所属を更新しました")

@router.post("/api/calendar/departments/{department_id}/archive")
def archive_department(department_id: int, db: Session = Depends(get_db)):
    department = db.get(Department, department_id)
    if not department:
        return error("DEPARTMENT_NOT_FOUND", "所属が見つかりません")
    department.is_active = False
    add_audit_log(db, "archive_department", "department", department.id)
    db.commit()
    return success({"id": department.id}, "所属を無効化しました")

@router.get("/api/calendar/members/{member_id}/departments")
def list_member_departments(member_id: int, db: Session = Depends(get_db)):
    member = db.get(CalendarMember, member_id)
    if not member:
        return error("MEMBER_NOT_FOUND", "メンバーが見つかりません")
    member_departments = db.query(CalendarMemberDepartment).filter(CalendarMemberDepartment.member_id == member_id).all()
    return success([{
        "id": md.id,
        "department_id": md.department_id,
        "department_name": md.department.name if md.department else None,
    } for md in member_departments], "メンバーの所属一覧を取得しました")

@router.put("/api/calendar/members/{member_id}/departments")
def update_member_departments(member_id: int, payload: MemberDepartmentsUpdate, db: Session = Depends(get_db)):
    member = db.get(CalendarMember, member_id)
    if not member:
        return error("MEMBER_NOT_FOUND", "メンバーが見つかりません")
    
    existing = db.query(CalendarMemberDepartment).filter(CalendarMemberDepartment.member_id == member_id).all()
    for md in existing:
        db.delete(md)
    
    for dept_id in payload.department_ids:
        dept = db.get(Department, dept_id)
        if not dept:
            return error("DEPARTMENT_NOT_FOUND", f"所属ID {dept_id} が見つかりません")
        md = CalendarMemberDepartment(member_id=member_id, department_id=dept_id)
        db.add(md)
    
    add_audit_log(db, "update_member_departments", "calendar_member", member_id, request=payload.model_dump())
    db.commit()
    return success({"member_id": member_id, "department_ids": payload.department_ids}, "メンバーの所属を更新しました")

@router.get("/api/calendar/capacity-rules")
def list_capacity_rules(db: Session = Depends(get_db)):
    rules = db.query(CalendarEventTypeCapacityRule).order_by(CalendarEventTypeCapacityRule.id).all()
    return success([{
        "id": r.id,
        "event_type_id": r.event_type_id,
        "event_type_name": r.event_type.name if r.event_type else None,
        "department_id": r.department_id,
        "department_name": r.department.name if r.department else None,
        "day_type": r.day_type,
        "required_count": r.required_count,
        "is_active": r.is_active,
    } for r in rules], "定員ルール一覧を取得しました")

@router.post("/api/calendar/capacity-rules")
def create_capacity_rule(payload: CapacityRuleCreate, db: Session = Depends(get_db)):
    if not db.get(CalendarEventType, payload.event_type_id):
        return error("EVENT_TYPE_NOT_FOUND", "予定種類が見つかりません")
    if payload.department_id and not db.get(Department, payload.department_id):
        return error("DEPARTMENT_NOT_FOUND", "所属が見つかりません")
    
    rule = CalendarEventTypeCapacityRule(**payload.model_dump())
    db.add(rule)
    db.flush()
    add_audit_log(db, "create_capacity_rule", "capacity_rule", rule.id, request=payload.model_dump())
    db.commit()
    return success({"id": rule.id}, "定員ルールを作成しました")

@router.put("/api/calendar/capacity-rules/{rule_id}")
def update_capacity_rule(rule_id: int, payload: CapacityRuleUpdate, db: Session = Depends(get_db)):
    rule = db.get(CalendarEventTypeCapacityRule, rule_id)
    if not rule:
        return error("CAPACITY_RULE_NOT_FOUND", "定員ルールが見つかりません")
    
    if payload.event_type_id and not db.get(CalendarEventType, payload.event_type_id):
        return error("EVENT_TYPE_NOT_FOUND", "予定種類が見つかりません")
    if payload.department_id and not db.get(Department, payload.department_id):
        return error("DEPARTMENT_NOT_FOUND", "所属が見つかりません")
    
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    add_audit_log(db, "update_capacity_rule", "capacity_rule", rule.id, request=payload.model_dump(exclude_unset=True))
    db.commit()
    return success({"id": rule.id}, "定員ルールを更新しました")

@router.post("/api/calendar/capacity-rules/{rule_id}/archive")
def archive_capacity_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(CalendarEventTypeCapacityRule, rule_id)
    if not rule:
        return error("CAPACITY_RULE_NOT_FOUND", "定員ルールが見つかりません")
    rule.is_active = False
    add_audit_log(db, "archive_capacity_rule", "capacity_rule", rule.id)
    db.commit()
    return success({"id": rule.id}, "定員ルールを無効化しました")

@router.get("/api/calendar/studios")
def list_studios(db: Session = Depends(get_db)):
    studios = db.query(Studio).order_by(Studio.display_order, Studio.id).all()
    return success([{
        "id": s.id,
        "name": s.name,
        "code": s.code,
        "is_active": s.is_active,
        "display_order": s.display_order,
    } for s in studios], "スタジオ一覧を取得しました")

@router.post("/api/calendar/studios")
def create_studio(payload: StudioCreate, db: Session = Depends(get_db)):
    studio = Studio(**payload.model_dump())
    db.add(studio)
    db.flush()
    add_audit_log(db, "create_studio", "studio", studio.id, request=payload.model_dump())
    db.commit()
    return success({"id": studio.id}, "スタジオを作成しました")

@router.put("/api/calendar/studios/{studio_id}")
def update_studio(studio_id: int, payload: StudioUpdate, db: Session = Depends(get_db)):
    studio = db.get(Studio, studio_id)
    if not studio:
        return error("STUDIO_NOT_FOUND", "スタジオが見つかりません")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(studio, key, value)
    add_audit_log(db, "update_studio", "studio", studio.id, request=payload.model_dump(exclude_unset=True))
    db.commit()
    return success({"id": studio.id}, "スタジオを更新しました")

@router.post("/api/calendar/studios/{studio_id}/archive")
def archive_studio(studio_id: int, db: Session = Depends(get_db)):
    studio = db.get(Studio, studio_id)
    if not studio:
        return error("STUDIO_NOT_FOUND", "スタジオが見つかりません")
    studio.is_active = False
    add_audit_log(db, "archive_studio", "studio", studio.id)
    db.commit()
    return success({"id": studio.id}, "スタジオを無効化しました")

@router.get("/api/calendar/programs")
def list_programs(db: Session = Depends(get_db)):
    programs = db.query(Program).order_by(Program.display_order, Program.id).all()
    return success([{
        "id": p.id,
        "name": p.name,
        "code": p.code,
        "short_label": p.short_label,
        "display_color": p.display_color,
        "is_active": p.is_active,
        "display_order": p.display_order,
    } for p in programs], "番組一覧を取得しました")

@router.post("/api/calendar/programs")
def create_program(payload: ProgramCreate, db: Session = Depends(get_db)):
    program = Program(**payload.model_dump())
    db.add(program)
    db.flush()
    add_audit_log(db, "create_program", "program", program.id, request=payload.model_dump())
    db.commit()
    return success({"id": program.id}, "番組を作成しました")

@router.put("/api/calendar/programs/{program_id}")
def update_program(program_id: int, payload: ProgramUpdate, db: Session = Depends(get_db)):
    program = db.get(Program, program_id)
    if not program:
        return error("PROGRAM_NOT_FOUND", "番組が見つかりません")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(program, key, value)
    add_audit_log(db, "update_program", "program", program.id, request=payload.model_dump(exclude_unset=True))
    db.commit()
    return success({"id": program.id}, "番組を更新しました")

@router.post("/api/calendar/programs/{program_id}/archive")
def archive_program(program_id: int, db: Session = Depends(get_db)):
    program = db.get(Program, program_id)
    if not program:
        return error("PROGRAM_NOT_FOUND", "番組が見つかりません")
    program.is_active = False
    add_audit_log(db, "archive_program", "program", program.id)
    db.commit()
    return success({"id": program.id}, "番組を無効化しました")

@router.get("/api/calendar/program-schedules")
def list_program_schedules(year: int, month: int, db: Session = Depends(get_db)):
    from calendar import monthrange
    last_day = monthrange(year, month)[1]
    schedules = db.query(ProgramSchedule).filter(
        ProgramSchedule.event_date >= date(year, month, 1),
        ProgramSchedule.event_date <= date(year, month, last_day),
    ).all()
    return success([{
        "id": s.id,
        "program_id": s.program_id,
        "program_name": s.program.name if s.program else None,
        "program_short_label": s.program.short_label if s.program else None,
        "program_display_color": s.program.display_color if s.program else None,
        "studio_id": s.studio_id,
        "studio_name": s.studio.name if s.studio else None,
        "event_date": s.event_date.isoformat(),
    } for s in schedules], "番組スケジュール一覧を取得しました")

@router.post("/api/calendar/program-schedules")
def create_program_schedule(payload: ProgramScheduleCreate, db: Session = Depends(get_db)):
    if not db.get(Program, payload.program_id):
        return error("PROGRAM_NOT_FOUND", "番組が見つかりません")
    if not db.get(Studio, payload.studio_id):
        return error("STUDIO_NOT_FOUND", "スタジオが見つかりません")
    
    schedule = ProgramSchedule(**payload.model_dump())
    db.add(schedule)
    db.flush()
    add_audit_log(db, "create_program_schedule", "program_schedule", schedule.id, request=payload.model_dump())
    db.commit()
    return success({"id": schedule.id}, "番組スケジュールを作成しました")

@router.delete("/api/calendar/program-schedules/{schedule_id}")
def delete_program_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.get(ProgramSchedule, schedule_id)
    if not schedule:
        return error("PROGRAM_SCHEDULE_NOT_FOUND", "番組スケジュールが見つかりません")
    db.delete(schedule)
    add_audit_log(db, "delete_program_schedule", "program_schedule", schedule_id)
    db.commit()
    return success({"id": schedule_id}, "番組スケジュールを削除しました")

@router.post("/api/calendar/program-schedules/bulk")
def create_program_schedules_bulk(payload: ProgramScheduleBulkCreate, db: Session = Depends(get_db)):
    success_count = 0
    error_count = 0
    errors = []
    created_ids = []

    for idx, schedule_data in enumerate(payload.schedules):
        try:
            # Resolve program_id from program_name if not provided
            program_id = schedule_data.program_id
            if program_id is None and schedule_data.program_name:
                program = db.query(Program).filter(
                    Program.name == schedule_data.program_name,
                    Program.is_active == True
                ).first()
                if not program:
                    errors.append({
                        "index": idx,
                        "error": "PROGRAM_NOT_FOUND",
                        "message": f"番組名 '{schedule_data.program_name}' が見つかりません",
                        "data": schedule_data.model_dump()
                    })
                    error_count += 1
                    continue
                program_id = program.id
            elif program_id is None:
                errors.append({
                    "index": idx,
                    "error": "PROGRAM_REQUIRED",
                    "message": "program_id または program_name のいずれかを指定してください",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            program = db.get(Program, program_id)
            if not program:
                errors.append({
                    "index": idx,
                    "error": "PROGRAM_NOT_FOUND",
                    "message": f"番組ID {program_id} が見つかりません",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            # Resolve studio_id from studio_name if not provided
            studio_id = schedule_data.studio_id
            if studio_id is None and schedule_data.studio_name:
                studio = db.query(Studio).filter(
                    Studio.name == schedule_data.studio_name,
                    Studio.is_active == True
                ).first()
                if not studio:
                    errors.append({
                        "index": idx,
                        "error": "STUDIO_NOT_FOUND",
                        "message": f"スタジオ名 '{schedule_data.studio_name}' が見つかりません",
                        "data": schedule_data.model_dump()
                    })
                    error_count += 1
                    continue
                studio_id = studio.id
            elif studio_id is None:
                errors.append({
                    "index": idx,
                    "error": "STUDIO_REQUIRED",
                    "message": "studio_id または studio_name のいずれかを指定してください",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            studio = db.get(Studio, studio_id)
            if not studio:
                errors.append({
                    "index": idx,
                    "error": "STUDIO_NOT_FOUND",
                    "message": f"スタジオID {studio_id} が見つかりません",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            # Check for duplicate schedules
            existing = db.query(ProgramSchedule).filter(
                ProgramSchedule.program_id == program_id,
                ProgramSchedule.studio_id == studio_id,
                ProgramSchedule.event_date == schedule_data.event_date,
            ).first()
            if existing:
                errors.append({
                    "index": idx,
                    "error": "DUPLICATE_SCHEDULE",
                    "message": "同一番組・同一スタジオ・同日のスケジュールが既に存在します",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            schedule = ProgramSchedule(
                program_id=program_id,
                studio_id=studio_id,
                event_date=schedule_data.event_date
            )
            db.add(schedule)
            db.flush()
            add_audit_log(db, "create_program_schedule_bulk", "program_schedule", schedule.id, request=schedule_data.model_dump())
            created_ids.append(schedule.id)
            success_count += 1

        except Exception as e:
            errors.append({
                "index": idx,
                "error": "INTERNAL_ERROR",
                "message": str(e),
                "data": schedule_data.model_dump()
            })
            error_count += 1

    db.commit()

    return success({
        "success_count": success_count,
        "error_count": error_count,
        "created_ids": created_ids,
        "errors": errors
    }, f"バルクインポート完了: 成功 {success_count}件, 失敗 {error_count}件")

## History Events API

@router.get("/api/calendar/history-events")
def list_history_events(
    member_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    event_type_id: int | None = None,
    db: Session = Depends(get_db)
):
    from sqlalchemy import func
    query = db.query(HistoryEvent)

    if member_id:
        query = query.filter(HistoryEvent.member_id == member_id)
    if year:
        query = query.filter(func.extract('year', HistoryEvent.event_date) == year)
    if month:
        query = query.filter(func.extract('month', HistoryEvent.event_date) == month)
    if event_type_id:
        query = query.filter(HistoryEvent.event_type_id == event_type_id)

    events = query.order_by(HistoryEvent.event_date.desc()).all()
    return success([{
        "id": e.id,
        "member_id": e.member_id,
        "member_display_name": e.member_display_name,
        "event_date": e.event_date.isoformat(),
        "event_type_id": e.event_type_id,
        "event_type_name": e.event_type_name,
        "event_type_code": e.event_type_code,
        "title": e.title,
        "display_label": e.display_label,
        "memo": e.memo,
        "source_type": e.source_type,
        "source_detail": e.source_detail,
        "original_event_id": e.original_event_id,
        "archived_at": e.archived_at.isoformat() if e.archived_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    } for e in events], "履歴イベント一覧を取得しました")

@router.post("/api/calendar/history-events/archive")
def archive_events(
    cutoff_date: date | None = None,
    db: Session = Depends(get_db)
):
    result = archive_old_events(db, cutoff_date)
    return success(result, f"{result['archived_count']}件のイベントを履歴にアーカイブしました")

## History Aggregation API

@router.get("/api/calendar/history-aggregations")
def list_history_aggregations(
    member_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    event_type_id: int | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(HistoryAggregation)

    if member_id:
        query = query.filter(HistoryAggregation.member_id == member_id)
    if year:
        query = query.filter(HistoryAggregation.year == year)
    if month:
        query = query.filter(HistoryAggregation.month == month)
    if event_type_id:
        query = query.filter(HistoryAggregation.event_type_id == event_type_id)

    aggregations = query.order_by(HistoryAggregation.year.desc(), HistoryAggregation.month.desc()).all()
    return success([{
        "id": a.id,
        "member_id": a.member_id,
        "member_display_name": a.member_display_name,
        "year": a.year,
        "month": a.month,
        "event_type_id": a.event_type_id,
        "event_type_name": a.event_type_name,
        "event_type_code": a.event_type_code,
        "count": a.count,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    } for a in aggregations], "履歴集計一覧を取得しました")

@router.post("/api/calendar/history-aggregations/update")
def update_aggregations(db: Session = Depends(get_db)):
    result = update_history_aggregations(db)
    return success(result, f"{result['created_count']}件の集計データを更新しました")

## Search API

@router.get("/api/calendar/search")
def search_events(
    start_date: date | None = None,
    end_date: date | None = None,
    member_id: int | None = None,
    member_name: str | None = None,
    event_type_id: int | None = None,
    event_type_name: str | None = None,
    department_id: int | None = None,
    department_name: str | None = None,
    studio_id: int | None = None,
    studio_name: str | None = None,
    program_id: int | None = None,
    program_name: str | None = None,
    db: Session = Depends(get_db)
):
    """
    柔軟な検索API。複数の条件を組み合わせて検索できます。
    """
    query = db.query(CalendarEvent).filter(CalendarEvent.is_archived == False)

    # Date range filter
    if start_date:
        query = query.filter(CalendarEvent.event_date >= start_date)
    if end_date:
        query = query.filter(CalendarEvent.event_date <= end_date)

    # Member filter
    if member_id:
        query = query.filter(CalendarEvent.member_id == member_id)
    elif member_name:
        member = db.query(CalendarMember).filter(
            CalendarMember.display_name == member_name,
            CalendarMember.is_active == True
        ).first()
        if member:
            query = query.filter(CalendarEvent.member_id == member.id)

    # Event type filter
    if event_type_id:
        query = query.filter(CalendarEvent.event_type_id == event_type_id)
    elif event_type_name:
        event_type = db.query(CalendarEventType).filter(
            CalendarEventType.name == event_type_name,
            CalendarEventType.is_active == True
        ).first()
        if event_type:
            query = query.filter(CalendarEvent.event_type_id == event_type.id)

    # Department filter (through member departments)
    if department_id:
        member_ids = db.query(CalendarMemberDepartment.member_id).filter(
            CalendarMemberDepartment.department_id == department_id
        ).all()
        member_ids = [m[0] for m in member_ids]
        if member_ids:
            query = query.filter(CalendarEvent.member_id.in_(member_ids))
    elif department_name:
        department = db.query(Department).filter(
            Department.name == department_name,
            Department.is_active == True
        ).first()
        if department:
            member_ids = db.query(CalendarMemberDepartment.member_id).filter(
                CalendarMemberDepartment.department_id == department.id
            ).all()
            member_ids = [m[0] for m in member_ids]
            if member_ids:
                query = query.filter(CalendarEvent.member_id.in_(member_ids))

    events = query.order_by(CalendarEvent.event_date.asc(), CalendarEvent.member_id.asc()).all()

    return success([{
        "id": e.id,
        "member_id": e.member_id,
        "member_name": e.member.display_name if e.member else None,
        "event_date": e.event_date.isoformat(),
        "event_type_id": e.event_type_id,
        "event_type_name": e.event_type.name if e.event_type else None,
        "title": e.title,
        "display_label": e.display_label,
        "memo": e.memo,
    } for e in events], "検索結果を取得しました")

@router.get("/api/calendar/search/programs")
def search_program_schedules(
    start_date: date | None = None,
    end_date: date | None = None,
    program_id: int | None = None,
    program_name: str | None = None,
    studio_id: int | None = None,
    studio_name: str | None = None,
    db: Session = Depends(get_db)
):
    """
    番組スケジュールの柔軟な検索API。
    """
    query = db.query(ProgramSchedule)

    # Date range filter
    if start_date:
        query = query.filter(ProgramSchedule.event_date >= start_date)
    if end_date:
        query = query.filter(ProgramSchedule.event_date <= end_date)

    # Program filter
    if program_id:
        query = query.filter(ProgramSchedule.program_id == program_id)
    elif program_name:
        program = db.query(Program).filter(
            Program.name == program_name,
            Program.is_active == True
        ).first()
        if program:
            query = query.filter(ProgramSchedule.program_id == program.id)

    # Studio filter
    if studio_id:
        query = query.filter(ProgramSchedule.studio_id == studio_id)
    elif studio_name:
        studio = db.query(Studio).filter(
            Studio.name == studio_name,
            Studio.is_active == True
        ).first()
        if studio:
            query = query.filter(ProgramSchedule.studio_id == studio.id)

    schedules = query.order_by(ProgramSchedule.event_date.asc()).all()

    return success([{
        "id": s.id,
        "program_id": s.program_id,
        "program_name": s.program.name if s.program else None,
        "program_short_label": s.program.short_label if s.program else None,
        "studio_id": s.studio_id,
        "studio_name": s.studio.name if s.studio else None,
        "event_date": s.event_date.isoformat(),
    } for s in schedules], "番組スケジュール検索結果を取得しました")

## AI Reference API

# Allowed tools for AI
ALLOWED_AI_TOOLS = {
    "calendar_events_search",
    "calendar_members_list",
    "calendar_capacity_summary"
}

# Tool definitions
TOOL_DEFINITIONS = {
    "calendar_events_search": {
        "name": "calendar_events_search",
        "description": "Search calendar events by various filters",
        "allowed_filters": ["year", "month", "start_date", "end_date", "member_name", "event_name", "event_type_name", "source_type"],
        "max_limit": 100,
        "max_date_range_days": 365
    },
    "calendar_members_list": {
        "name": "calendar_members_list",
        "description": "List calendar members with optional filters",
        "allowed_filters": ["department_name", "is_active"],
        "max_limit": 100,
        "max_date_range_days": None
    },
    "calendar_capacity_summary": {
        "name": "calendar_capacity_summary",
        "description": "Get capacity summary for a given year/month and event types",
        "allowed_filters": ["year", "month", "event_type_name"],
        "max_limit": 50,
        "max_date_range_days": 31
    }
}

@router.get("/api/dev/tables")
def list_tables(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """List all database tables (Developer only)"""
    try:
        verify_dev_key(authorization)
    except HTTPException as e:
        logger.warning(f"Dev tables access denied: {e.detail}")
        raise

    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    logger.info(f"Dev tables listed: {len(tables)} tables")
    add_audit_log(db, "dev_tables", "system", None, request={"action": "list_tables", "count": len(tables)})

    return success({"tables": tables}, "Tables listed")

@router.get("/api/dev/tables/{table_name}")
def get_table_data(
    table_name: str,
    limit: int = 100,
    offset: int = 0,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get data from a specific table (Developer only)"""
    try:
        verify_dev_key(authorization)
    except HTTPException as e:
        logger.warning(f"Dev table data access denied: {e.detail}")
        raise

    from sqlalchemy import inspect, text

    # Validate table name
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        logger.warning(f"Dev table data: table not found - {table_name}")
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    # Get column info
    columns = inspector.get_columns(table_name)
    column_names = [col['name'] for col in columns]

    # Execute query
    query = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")
    result = db.execute(query, {"limit": limit, "offset": offset})
    rows = result.fetchall()

    # Convert to dict
    data = []
    for row in rows:
        row_dict = {}
        for i, col_name in enumerate(column_names):
            value = row[i]
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            row_dict[col_name] = value
        data.append(row_dict)

    # Get total count
    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
    total_result = db.execute(count_query)
    total = total_result.scalar()

    logger.info(f"Dev table data retrieved: {table_name}, {len(data)} rows")
    add_audit_log(db, "dev_table_data", "system", None, request={
        "action": "get_table_data",
        "table_name": table_name,
        "limit": limit,
        "offset": offset,
        "result_count": len(data)
    })

    return success({
        "table_name": table_name,
        "columns": column_names,
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset
    }, f"Data from table '{table_name}' retrieved")

@router.get("/api/ai/calendar/capabilities")
def get_ai_capabilities(
    tool_name: str | None = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Return available AI reference tools"""
    try:
        verify_ai_read_key(authorization)
    except HTTPException as e:
        logger.warning(f"AI capabilities access denied: {e.detail}")
        raise
    
    logger.info(f"AI capabilities requested: tool_name={tool_name}")
    add_audit_log(db, "ai_capabilities", "system", None, request={"action": "get_capabilities", "tool_name": tool_name})
    
    tools_data = [
        {
            "name": tool_name_item,
            "description": tool_def["description"],
            "allowed_filters": tool_def["allowed_filters"],
            "max_limit": tool_def["max_limit"]
        }
        for tool_name_item, tool_def in TOOL_DEFINITIONS.items()
    ]
    
    # Filter by tool_name if specified
    if tool_name:
        tools_data = [t for t in tools_data if t["name"] == tool_name]
    
    return success({"tools": tools_data}, "AI capabilities retrieved")

@router.get("/api/ai/calendar/search")
def ai_search(
    tool: str,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    member_name: str | None = None,
    event_name: str | None = None,
    event_type_name: str | None = None,
    source_type: str | None = None,
    department_name: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Search AI reference tools via GET with query parameters"""
    try:
        verify_ai_read_key(authorization)
    except HTTPException as e:
        logger.warning(f"AI search access denied: {e.detail}")
        raise
    
    # Validate tool
    if tool not in ALLOWED_AI_TOOLS:
        logger.warning(f"AI search: tool not allowed - {tool}")
        raise HTTPException(status_code=400, detail=f"Tool '{tool}' not allowed")
    
    tool_def = TOOL_DEFINITIONS[tool]
    
    # Validate limit
    if limit > tool_def["max_limit"]:
        logger.warning(f"AI search: limit exceeded - {limit} > {tool_def['max_limit']}")
        raise HTTPException(status_code=400, detail=f"Limit exceeds maximum of {tool_def['max_limit']}")
    
    # Build filters based on tool
    filters = {}
    
    if tool == "calendar_events_search":
        if year is not None:
            filters["year"] = year
        if month is not None:
            filters["month"] = month
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        if member_name:
            filters["member_name"] = member_name
        if event_name:
            filters["event_name"] = event_name
        if event_type_name:
            filters["event_type_name"] = event_type_name
        if source_type:
            filters["source_type"] = source_type
    
    elif tool == "calendar_members_list":
        if department_name:
            filters["department_name"] = department_name
        if is_active is not None:
            filters["is_active"] = is_active
    
    elif tool == "calendar_capacity_summary":
        if year is not None:
            filters["year"] = year
        if month is not None:
            filters["month"] = month
        if event_type_name:
            filters["event_type_name"] = event_type_name
    
    # Validate date range
    if tool_def["max_date_range_days"] and "start_date" in filters and "end_date" in filters:
        try:
            start = date.fromisoformat(filters["start_date"])
            end = date.fromisoformat(filters["end_date"])
            if (end - start).days > tool_def["max_date_range_days"]:
                logger.warning(f"AI search: date range too large - {(end - start).days} days")
                raise HTTPException(status_code=400, detail=f"Date range exceeds maximum of {tool_def['max_date_range_days']} days")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Execute tool
    logger.info(f"AI search executing: {tool}")
    result = execute_ai_tool(tool, filters, limit, db)
    
    add_audit_log(db, "ai_search", "system", None, request={
        "tool": tool,
        "filters": {k: v for k, v in filters.items() if k not in ["member_name", "event_name"]},
        "limit": limit,
        "result_count": len(result.get("data", [])) if isinstance(result, dict) else 0
    })
    
    return success(result, f"AI search '{tool}' executed")

@router.post("/api/ai/calendar/query")
def ai_query(
    request_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Execute a single AI reference tool query"""
    try:
        verify_ai_read_key(authorization)
    except HTTPException as e:
        logger.warning(f"AI query access denied: {e.detail}")
        raise
    
    tool_name = request_data.get("tool")
    filters = request_data.get("filters", {})
    limit = request_data.get("limit", 50)
    
    # Validate tool
    if tool_name not in ALLOWED_AI_TOOLS:
        logger.warning(f"AI query: tool not allowed - {tool_name}")
        add_audit_log(db, "ai_query", "system", None, request={"tool": tool_name, "error": "tool_not_allowed"})
        raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' not allowed")
    
    tool_def = TOOL_DEFINITIONS[tool_name]
    
    # Validate limit
    if limit > tool_def["max_limit"]:
        logger.warning(f"AI query: limit exceeded - {limit} > {tool_def['max_limit']}")
        raise HTTPException(status_code=400, detail=f"Limit exceeds maximum of {tool_def['max_limit']}")
    
    # Validate filters
    for filter_key in filters.keys():
        if filter_key not in tool_def["allowed_filters"]:
            logger.warning(f"AI query: filter not allowed - {filter_key}")
            raise HTTPException(status_code=400, detail=f"Filter '{filter_key}' not allowed for tool '{tool_name}'")
    
    # Validate date range
    if tool_def["max_date_range_days"] and "start_date" in filters and "end_date" in filters:
        try:
            start = date.fromisoformat(filters["start_date"])
            end = date.fromisoformat(filters["end_date"])
            if (end - start).days > tool_def["max_date_range_days"]:
                logger.warning(f"AI query: date range too large - {(end - start).days} days")
                raise HTTPException(status_code=400, detail=f"Date range exceeds maximum of {tool_def['max_date_range_days']} days")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Execute tool
    logger.info(f"AI query executing: {tool_name}")
    result = execute_ai_tool(tool_name, filters, limit, db)
    
    add_audit_log(db, "ai_query", "system", None, request={
        "tool": tool_name,
        "filters": {k: v for k, v in filters.items() if k not in ["member_name", "event_name"]},
        "limit": limit,
        "result_count": len(result.get("data", []))
    })
    
    return success(result, f"AI query '{tool_name}' executed")

@router.post("/api/ai/calendar/query-batch")
def ai_query_batch(
    request_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Execute multiple AI reference tool queries in a single iteration"""
    try:
        verify_ai_read_key(authorization)
    except HTTPException as e:
        logger.warning(f"AI query-batch access denied: {e.detail}")
        raise
    
    queries = request_data.get("queries", [])
    iteration = request_data.get("iteration", 1)
    
    # Validate number of queries
    if len(queries) > 3:
        logger.warning(f"AI query-batch: too many queries - {len(queries)}")
        raise HTTPException(status_code=400, detail="Maximum 3 queries per batch")
    
    logger.info(f"AI query-batch executing: iteration {iteration}, {len(queries)} queries")
    
    results = []
    for query in queries:
        tool_name = query.get("tool")
        filters = query.get("filters", {})
        limit = query.get("limit", 50)
        
        try:
            # Validate tool
            if tool_name not in ALLOWED_AI_TOOLS:
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": f"Tool '{tool_name}' not allowed"
                })
                continue
            
            tool_def = TOOL_DEFINITIONS[tool_name]
            
            # Validate limit
            if limit > tool_def["max_limit"]:
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": f"Limit exceeds maximum of {tool_def['max_limit']}"
                })
                continue
            
            # Validate filters
            for filter_key in filters.keys():
                if filter_key not in tool_def["allowed_filters"]:
                    results.append({
                        "tool": tool_name,
                        "success": False,
                        "error": f"Filter '{filter_key}' not allowed"
                    })
                    continue
            
            # Validate date range
            if tool_def["max_date_range_days"] and "start_date" in filters and "end_date" in filters:
                try:
                    start = date.fromisoformat(filters["start_date"])
                    end = date.fromisoformat(filters["end_date"])
                    if (end - start).days > tool_def["max_date_range_days"]:
                        results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": f"Date range exceeds maximum of {tool_def['max_date_range_days']} days"
                        })
                        continue
                except ValueError:
                    results.append({
                        "tool": tool_name,
                        "success": False,
                        "error": "Invalid date format"
                    })
                    continue
            
            # Execute tool
            result = execute_ai_tool(tool_name, filters, limit, db)
            results.append({
                "tool": tool_name,
                "success": True,
                "data": result
            })
            
        except Exception as e:
            logger.error(f"AI query-batch error for {tool_name}: {str(e)}")
            results.append({
                "tool": tool_name,
                "success": False,
                "error": str(e)
            })
    
    add_audit_log(db, "ai_query_batch", "system", None, request={
        "iteration": iteration,
        "query_count": len(queries),
        "success_count": sum(1 for r in results if r.get("success"))
    })
    
    return success({
        "iteration": iteration,
        "results": results
    }, f"AI query-batch executed: iteration {iteration}")

def execute_ai_tool(tool_name: str, filters: dict, limit: int, db: Session) -> dict:
    """Execute a specific AI tool"""
    if tool_name == "calendar_events_search":
        return tool_calendar_events_search(filters, limit, db)
    elif tool_name == "calendar_members_list":
        return tool_calendar_members_list(filters, limit, db)
    elif tool_name == "calendar_capacity_summary":
        return tool_calendar_capacity_summary(filters, limit, db)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

def tool_calendar_events_search(filters: dict, limit: int, db: Session) -> dict:
    """Search calendar events"""
    query = db.query(CalendarEvent).filter(CalendarEvent.is_archived == False)
    
    # Year/Month filter
    if "year" in filters and "month" in filters:
        year = filters["year"]
        month = filters["month"]
        from calendar import monthrange
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        query = query.filter(CalendarEvent.event_date >= start_date, CalendarEvent.event_date <= end_date)
    
    # Date range filter
    if "start_date" in filters:
        query = query.filter(CalendarEvent.event_date >= date.fromisoformat(filters["start_date"]))
    if "end_date" in filters:
        query = query.filter(CalendarEvent.event_date <= date.fromisoformat(filters["end_date"]))
    
    # Member name filter
    if "member_name" in filters:
        member = db.query(CalendarMember).filter(
            CalendarMember.display_name == filters["member_name"],
            CalendarMember.is_active == True
        ).first()
        if member:
            query = query.filter(CalendarEvent.member_id == member.id)
    
    # Event name filter
    if "event_name" in filters:
        query = query.filter(CalendarEvent.title.ilike(f"%{filters['event_name']}%"))
    
    # Event type name filter
    if "event_type_name" in filters:
        event_type = db.query(CalendarEventType).filter(
            CalendarEventType.name == filters["event_type_name"],
            CalendarEventType.is_active == True
        ).first()
        if event_type:
            query = query.filter(CalendarEvent.event_type_id == event_type.id)
    
    # Source type filter
    if "source_type" in filters:
        query = query.filter(CalendarEvent.source_type == filters["source_type"])
    
    events = query.order_by(CalendarEvent.event_date.asc()).limit(limit).all()
    
    return {
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "member_name": e.member.display_name if e.member else None,
                "event_date": e.event_date.isoformat(),
                "event_type_name": e.event_type.name if e.event_type else None,
                "title": e.title,
                "display_label": e.display_label,
                "source_type": e.source_type
            }
            for e in events
        ]
    }

def tool_calendar_members_list(filters: dict, limit: int, db: Session) -> dict:
    """List calendar members"""
    query = db.query(CalendarMember)
    
    # Department name filter
    if "department_name" in filters:
        department = db.query(Department).filter(
            Department.name == filters["department_name"],
            Department.is_active == True
        ).first()
        if department:
            member_ids = db.query(CalendarMemberDepartment.member_id).filter(
                CalendarMemberDepartment.department_id == department.id
            ).all()
            member_ids = [m[0] for m in member_ids]
            if member_ids:
                query = query.filter(CalendarMember.id.in_(member_ids))
    
    # Active filter
    if "is_active" in filters:
        query = query.filter(CalendarMember.is_active == filters["is_active"])
    
    members = query.order_by(CalendarMember.display_order, CalendarMember.id).limit(limit).all()
    
    return {
        "count": len(members),
        "members": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "short_name": m.short_name,
                "is_active": m.is_active
            }
            for m in members
        ]
    }

def tool_calendar_capacity_summary(filters: dict, limit: int, db: Session) -> dict:
    """Get capacity summary"""
    if "year" not in filters or "month" not in filters:
        raise HTTPException(status_code=400, detail="year and month are required")
    
    year = filters["year"]
    month = filters["month"]
    from calendar import monthrange
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])
    
    # Get capacity rules
    rules = db.query(CalendarEventTypeCapacityRule).filter(
        CalendarEventTypeCapacityRule.is_active == True
    ).all()
    
    summary = []
    for rule in rules:
        # Filter by event type name if specified
        if "event_type_name" in filters:
            if rule.event_type.name != filters["event_type_name"]:
                continue
        
        # Check each day in the month
        daily_summary = []
        for day in range(1, monthrange(year, month)[1] + 1):
            current_date = date(year, month, day)
            
            # Get current count for this day
            current_count = db.query(CalendarEvent).filter(
                CalendarEvent.event_date == current_date,
                CalendarEvent.event_type_id == rule.event_type_id,
                CalendarEvent.is_archived == False
            ).count()
            
            daily_summary.append({
                "date": current_date.isoformat(),
                "required": rule.required_count,
                "current": current_count,
                "sufficient": current_count >= rule.required_count
            })
        
        summary.append({
            "event_type_name": rule.event_type.name,
            "department_name": rule.department.name if rule.department else None,
            "day_type": rule.day_type,
            "daily": daily_summary
        })
    
    return {
        "count": len(summary),
        "summaries": summary
    }

## Chat API

@router.post("/api/chat/dify-proxy")
async def dify_proxy(request: Request, db: Session = Depends(get_db)):
    """Proxy for UI chat to Dify Workflow - keeps Dify API key server-side"""
    import httpx

    body = await request.json()
    message = body.get("message", "")
    year = body.get("year")
    month = body.get("month")
    conversation_history = body.get("conversation_history", [])

    if not message:
        return error("INVALID_REQUEST", "メッセージが空です")

    # Dify Workflow API configuration
    dify_workflow_api_url = os.getenv("DIFY_WORKFLOW_API_URL", "")
    dify_workflow_api_key = os.getenv("DIFY_WORKFLOW_API_KEY", "")

    if not dify_workflow_api_key:
        logger.warning("DIFY_WORKFLOW_API_KEY not configured")
        return error("DIFY_NOT_CONFIGURED", "Dify Workflow APIキーが設定されていません")

    logger.info(f"Dify Workflow proxy called: year={year}, month={month}")
    add_audit_log(db, "dify_workflow_proxy", "system", None, request={
        "year": year,
        "month": month,
        "message_length": len(message)
    })

    try:
        async with httpx.AsyncClient() as client:
            # Build capabilities for AI reference tools
            capabilities = {
                "tools": [
                    {
                        "name": "calendar_events_search",
                        "max_limit": 100,
                        "allowed_filters": [
                            "year",
                            "month",
                            "date_from",
                            "date_to",
                            "member_name",
                            "source_type",
                        ],
                    },
                    {
                        "name": "calendar_members_list",
                        "max_limit": 100,
                        "allowed_filters": ["is_active"],
                    },
                    {
                        "name": "calendar_capacity_summary",
                        "max_limit": 50,
                        "allowed_filters": [
                            "year",
                            "month",
                            "date_from",
                            "date_to",
                            "department",
                        ],
                    },
                ]
            }

            # Build inputs with all required fields for Workflow API
            inputs = {
                "query": message,
                "current_year": str(year) if year else "2026",
                "current_month": str(month) if month else "6",
                "capabilities": json.dumps(capabilities, ensure_ascii=False),
            }

            # Add conversation history if available
            if conversation_history:
                inputs["conversation_history"] = json.dumps(conversation_history, ensure_ascii=False)

            response = await client.post(
                dify_workflow_api_url,
                headers={
                    "Authorization": f"Bearer {dify_workflow_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": inputs,
                    "response_mode": "blocking",
                    "user": "rd-ict",
                },
                timeout=60.0
            )

            if response.status_code == 200:
                data = response.json()
                # Workflow API response structure: data.outputs.final_answer
                reply = data.get("data", {}).get("outputs", {}).get("final_answer", "")
                if not reply:
                    reply = data.get("data", {}).get("outputs", {}).get("result", "")
                if not reply:
                    reply = data.get("data", {}).get("result", "")
                if not reply:
                    reply = str(data)
                logger.info(f"Dify Workflow proxy response received: {len(reply)} chars")
                return success({"reply": reply}, "AI応答を取得しました")
            else:
                logger.error(f"Dify Workflow API error: {response.status_code} - {response.text}")
                return error("DIFY_API_ERROR", f"Dify Workflow APIエラー: {response.status_code}")

    except httpx.TimeoutException:
        logger.error("Dify Workflow proxy timeout")
        return error("TIMEOUT_ERROR", "AI応答がタイムアウトしました")
    except Exception as e:
        logger.error(f"Dify Workflow proxy error: {str(e)}")
        return error("INTERNAL_ERROR", f"エラーが発生しました: {str(e)}")
