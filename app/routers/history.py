import logging
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import HistoryEvent, HistoryAggregation
from ..schemas import success, error
from ..services import archive_old_events, update_history_aggregations

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/calendar/history-events")
def list_history_events(
    member_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    event_type_id: int | None = None,
    db: Session = Depends(get_db)
):
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
