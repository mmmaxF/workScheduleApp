import logging
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import CalendarEvent, CalendarMember, CalendarEventType, Department, CalendarMemberDepartment, Program, Studio, ProgramSchedule
from ..schemas import success, error

logger = logging.getLogger(__name__)
router = APIRouter()

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
