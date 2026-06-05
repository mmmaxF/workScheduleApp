import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Department, CalendarMember, CalendarMemberDepartment
from ..schemas import DepartmentCreate, DepartmentUpdate, MemberDepartmentsUpdate, success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

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
