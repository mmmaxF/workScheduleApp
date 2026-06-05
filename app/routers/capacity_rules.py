import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import CalendarEventType, Department, CalendarEventTypeCapacityRule
from ..schemas import CapacityRuleCreate, CapacityRuleUpdate, success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

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
