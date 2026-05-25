import json
import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .database import get_db
from .models import CalendarMember, CalendarEventType, CalendarEventDraft, CalendarEvent
from .schemas import MemberCreate, MemberUpdate, EventTypeCreate, EventTypeUpdate, DraftCreate, EventCreate, success, error
from .services import validate_draft, approve_draft, build_monthly_calendar, add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

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

@router.post("/api/calendar/drafts")
def create_draft(payload: DraftCreate, db: Session = Depends(get_db)):
    draft = CalendarEventDraft(**payload.model_dump())
    db.add(draft)
    db.flush()
    add_audit_log(db, "create_draft", "calendar_event_draft", draft.id, request=payload.model_dump())
    db.commit()
    return success({"id": draft.id}, "draftを作成しました")

@router.get("/api/calendar/drafts")
def list_drafts(db: Session = Depends(get_db)):
    drafts = db.query(CalendarEventDraft).order_by(CalendarEventDraft.id.desc()).all()
    return success([{
        "id": d.id,
        "member_name_raw": d.member_name_raw,
        "member_id": d.member_id,
        "member_name": d.member.display_name if d.member else None,
        "event_date": d.event_date.isoformat(),
        "event_type_name_raw": d.event_type_name_raw,
        "event_type_id": d.event_type_id,
        "event_type_name": d.event_type.name if d.event_type else None,
        "title": d.title,
        "display_label": d.display_label,
        "source_type": d.source_type,
        "validation_status": d.validation_status,
        "approval_status": d.approval_status,
    } for d in drafts], "draft一覧を取得しました")

@router.post("/api/calendar/drafts/{draft_id}/validate")
def validate_draft_api(draft_id: int, db: Session = Depends(get_db)):
    draft = db.get(CalendarEventDraft, draft_id)
    if not draft:
        return error("DRAFT_NOT_FOUND", "draftが見つかりません")
    result = validate_draft(db, draft)
    add_audit_log(db, "validate_draft", "calendar_event_draft", draft.id, response=result)
    db.commit()
    if not result["valid"]:
        return error("VALIDATION_ERROR", "入力内容に不備があります", result["details"], result["suggestion"])
    return success(result, "draft検証が完了しました")

@router.post("/api/calendar/drafts/{draft_id}/approve")
def approve_draft_api(draft_id: int, db: Session = Depends(get_db)):
    draft = db.get(CalendarEventDraft, draft_id)
    if not draft:
        return error("DRAFT_NOT_FOUND", "draftが見つかりません")
    if draft.approval_status == "approved":
        return error("ALREADY_APPROVED", "このdraftはすでに承認済みです")
    try:
        event = approve_draft(db, draft)
        db.commit()
        return success({"event_id": event.id}, "draftを承認し、正式予定を登録しました")
    except ValueError as e:
        db.rollback()
        try:
            details = json.loads(str(e))
        except Exception:
            details = [{"message": str(e)}]
        return error("VALIDATION_ERROR", "承認前の検証に失敗しました", details if isinstance(details, list) else details.get("details", []), "内容を修正して再度検証してください")

@router.post("/api/calendar/drafts/{draft_id}/reject")
def reject_draft_api(draft_id: int, db: Session = Depends(get_db)):
    draft = db.get(CalendarEventDraft, draft_id)
    if not draft:
        return error("DRAFT_NOT_FOUND", "draftが見つかりません")
    draft.approval_status = "rejected"
    add_audit_log(db, "reject_draft", "calendar_event_draft", draft.id)
    db.commit()
    return success({"id": draft.id}, "draftを却下しました")

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
    if not db.get(CalendarMember, payload.member_id):
        return error("MEMBER_NOT_FOUND", "メンバーが見つかりません")
    if not db.get(CalendarEventType, payload.event_type_id):
        return error("EVENT_TYPE_NOT_FOUND", "予定種類が見つかりません")
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

@router.get("/api/calendar/events/monthly")
def monthly_events(year: int, month: int, db: Session = Depends(get_db)):
    if month < 1 or month > 12:
        return error("INVALID_MONTH", "monthは1〜12で指定してください")
    data = build_monthly_calendar(db, year, month)
    return success(data, "月間予定を取得しました")
