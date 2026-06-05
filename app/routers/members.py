import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import CalendarMember
from ..schemas import MemberCreate, MemberUpdate, success, error
from ..services import add_audit_log

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
