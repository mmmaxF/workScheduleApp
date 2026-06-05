import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Studio
from ..schemas import StudioCreate, StudioUpdate, success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

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
