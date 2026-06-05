import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import CalendarEventType
from ..schemas import EventTypeCreate, EventTypeUpdate, success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

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
