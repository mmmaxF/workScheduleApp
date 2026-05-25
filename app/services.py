import json
import logging
from calendar import monthrange
from datetime import date
from sqlalchemy.orm import Session
from .models import CalendarMember, CalendarEventType, CalendarEventDraft, CalendarEvent, AuditLog

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

    if not event_type or not event_type.is_active:
        details.append({
            "error_code": "EVENT_TYPE_NOT_FOUND",
            "message": "予定種類が見つかりません",
            "value": draft.event_type_name_raw or draft.event_type_id,
        })

    if draft.member_id and draft.event_type_id:
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

    if details:
        draft.validation_status = "error"
        return {
            "valid": False,
            "details": details,
            "suggestion": "メンバー名、予定種類、日付、重複予定を確認してください。",
        }

    draft.validation_status = "valid"
    return {
        "valid": True,
        "details": [],
        "suggestion": "",
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

def build_monthly_calendar(db: Session, year: int, month: int) -> dict:
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

    members = db.query(CalendarMember).filter(CalendarMember.is_active == True).order_by(CalendarMember.display_order, CalendarMember.id).all()
    events = db.query(CalendarEvent).filter(
        CalendarEvent.event_date >= date(year, month, 1),
        CalendarEvent.event_date <= date(year, month, last_day),
        CalendarEvent.is_archived == False,
    ).all()

    by_member_date = {}
    for event in events:
        key = (event.member_id, event.event_date.isoformat())
        by_member_date.setdefault(key, []).append({
            "event_id": event.id,
            "event_type_id": event.event_type_id,
            "event_type": event.event_type.name if event.event_type else None,
            "display_label": event.display_label or event.title,
            "display_color": event.event_type.display_color if event.event_type else None,
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

    return {
        "year": year,
        "month": month,
        "days": days,
        "members": member_rows,
    }
