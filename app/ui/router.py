import logging
from datetime import date
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    CalendarMember,
    CalendarEventType,
    Department,
    CalendarMemberDepartment,
    CalendarEventTypeCapacityRule,
    CalendarEvent,
    Studio,
    Program,
    ProgramSchedule,
    RegularSchedule,
)
from ..services import build_monthly_calendar, add_audit_log, check_capacity

logger = logging.getLogger(__name__)
router = APIRouter()

templates = Jinja2Templates(directory="app/ui/templates")


@router.get("/", response_class=HTMLResponse)
def index():
    return RedirectResponse(url="/calendar")


@router.get("/dev/db-viewer", response_class=HTMLResponse)
def dev_db_viewer(request: Request):
    return templates.TemplateResponse("dev_db_viewer.html", {"request": request})


@router.get("/calendar", response_class=HTMLResponse)
def calendar_page(
    request: Request,
    year: int | None = None,
    month: int | None = None,
    department_id: int | None = None,
    db: Session = Depends(get_db),
):
    today = date.today()
    year = year or today.year
    month = month or today.month
    data = build_monthly_calendar(db, year, month, department_id)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    members = (
        db.query(CalendarMember)
        .filter(CalendarMember.is_active == True)
        .order_by(CalendarMember.display_order, CalendarMember.id)
        .all()
    )
    event_types = (
        db.query(CalendarEventType)
        .filter(CalendarEventType.is_active == True)
        .order_by(CalendarEventType.display_order, CalendarEventType.id)
        .all()
    )
    departments = (
        db.query(Department)
        .filter(Department.is_active == True)
        .order_by(Department.display_order, Department.id)
        .all()
    )
    programs = (
        db.query(Program)
        .filter(Program.is_active == True)
        .order_by(Program.display_order, Program.id)
        .all()
    )
    studios = (
        db.query(Studio)
        .filter(Studio.is_active == True)
        .order_by(Studio.display_order, Studio.id)
        .all()
    )
    regular_schedules = (
        db.query(RegularSchedule)
        .filter(RegularSchedule.is_active == True)
        .order_by(RegularSchedule.display_order, RegularSchedule.id)
        .all()
    )
    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "calendar": data,
            "members": members,
            "event_types": event_types,
            "departments": departments,
            "department_id": department_id,
            "programs": programs,
            "studios": studios,
            "regular_schedules": regular_schedules,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
        },
    )


@router.get("/masters", response_class=HTMLResponse)
def masters_page(request: Request, db: Session = Depends(get_db)):
    members = db.query(CalendarMember).order_by(CalendarMember.display_order, CalendarMember.id).all()
    event_types = (
        db.query(CalendarEventType).order_by(CalendarEventType.display_order, CalendarEventType.id).all()
    )
    departments = db.query(Department).order_by(Department.display_order, Department.id).all()
    member_departments = db.query(CalendarMemberDepartment).all()
    capacity_rules = (
        db.query(CalendarEventTypeCapacityRule).order_by(CalendarEventTypeCapacityRule.id).all()
    )
    studios = db.query(Studio).order_by(Studio.display_order, Studio.id).all()
    programs = db.query(Program).order_by(Program.display_order, Program.id).all()
    regular_schedules = db.query(RegularSchedule).order_by(RegularSchedule.display_order, RegularSchedule.id).all()
    return templates.TemplateResponse(
        "masters.html",
        {
            "request": request,
            "members": members,
            "event_types": event_types,
            "departments": departments,
            "member_departments": member_departments,
            "capacity_rules": capacity_rules,
            "studios": studios,
            "programs": programs,
            "regular_schedules": regular_schedules,
        },
    )


@router.post("/ui/members/create")
def ui_create_member(
    display_name: str = Form(...),
    short_name: str = Form(""),
    display_order: int = Form(100),
    department_ids: str = Form(""),
    db: Session = Depends(get_db),
):
    member = CalendarMember(display_name=display_name, short_name=short_name or None, display_order=display_order)
    db.add(member)
    db.flush()
    
    # Add departments
    if department_ids:
        dept_id_list = [int(x) for x in department_ids.split(",") if x.strip()]
        for dept_id in dept_id_list:
            dept = db.get(Department, dept_id)
            if dept:
                md = CalendarMemberDepartment(member_id=member.id, department_id=dept_id)
                db.add(md)
    
    add_audit_log(db, "ui_create_member", "calendar_member", member.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/members/update")
def ui_update_member(
    member_id: int = Form(...),
    display_name: str = Form(...),
    short_name: str = Form(""),
    display_order: int = Form(100),
    department_ids: str = Form(""),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
):
    member = db.get(CalendarMember, member_id)
    if not member:
        return RedirectResponse(url="/masters", status_code=303)
    member.display_name = display_name
    member.short_name = short_name or None
    member.display_order = display_order
    member.is_active = is_active
    
    # Update departments
    existing = db.query(CalendarMemberDepartment).filter(CalendarMemberDepartment.member_id == member_id).all()
    for md in existing:
        db.delete(md)
    
    if department_ids:
        dept_id_list = [int(x) for x in department_ids.split(",") if x.strip()]
        for dept_id in dept_id_list:
            dept = db.get(Department, dept_id)
            if dept:
                md = CalendarMemberDepartment(member_id=member_id, department_id=dept_id)
                db.add(md)
    
    add_audit_log(db, "ui_update_member", "calendar_member", member.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/members/{member_id}/archive")
def ui_archive_member(member_id: int, db: Session = Depends(get_db)):
    member = db.get(CalendarMember, member_id)
    if not member:
        return RedirectResponse(url="/masters", status_code=303)
    member.is_active = False
    add_audit_log(db, "ui_archive_member", "calendar_member", member.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/members/{member_id}/delete")
def ui_delete_member(member_id: int, db: Session = Depends(get_db)):
    member = db.get(CalendarMember, member_id)
    if not member:
        return RedirectResponse(url="/masters", status_code=303)
    # Delete member departments first
    db.query(CalendarMemberDepartment).filter(CalendarMemberDepartment.member_id == member_id).delete()
    db.delete(member)
    add_audit_log(db, "ui_delete_member", "calendar_member", member.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/event-types/create")
def ui_create_event_type(
    code: str = Form(""),
    name: str = Form(...),
    short_label: str = Form(""),
    display_color: str = Form(""),
    is_leave: bool = Form(False),
    is_work_assignment: bool = Form(False),
    requires_capacity_check: bool = Form(False),
    display_order: int = Form(100),
    db: Session = Depends(get_db),
):
    # Auto-generate code if not provided
    if not code:
        import re
        code = re.sub(r'[^a-zA-Z]', '', name).lower()[:10]
        if not code:
            code = f"evt_{name[:5]}"
        
        # Ensure unique code
        existing_codes = {et.code for et in db.query(CalendarEventType).all()}
        base_code = code
        counter = 1
        while code in existing_codes:
            code = f"{base_code}_{counter}"
            counter += 1
    
    item = CalendarEventType(
        code=code,
        name=name,
        short_label=short_label or name,
        display_color=display_color or None,
        is_leave=is_leave,
        is_work_assignment=is_work_assignment,
        requires_capacity_check=requires_capacity_check,
        display_order=display_order,
    )
    db.add(item)
    db.flush()
    add_audit_log(db, "ui_create_event_type", "calendar_event_type", item.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/event-types/update")
def ui_update_event_type(
    event_type_id: int = Form(...),
    code: str = Form(...),
    name: str = Form(...),
    short_label: str = Form(""),
    display_color: str = Form(""),
    is_leave: bool = Form(False),
    is_work_assignment: bool = Form(False),
    requires_capacity_check: bool = Form(False),
    display_order: int = Form(100),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
):
    item = db.get(CalendarEventType, event_type_id)
    if not item:
        return RedirectResponse(url="/masters", status_code=303)
    item.code = code
    item.name = name
    item.short_label = short_label or None
    item.display_color = display_color or None
    item.is_leave = is_leave
    item.is_work_assignment = is_work_assignment
    item.requires_capacity_check = requires_capacity_check
    item.display_order = display_order
    item.is_active = is_active
    add_audit_log(db, "ui_update_event_type", "calendar_event_type", item.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/event-types/{event_type_id}/archive")
def ui_archive_event_type(event_type_id: int, db: Session = Depends(get_db)):
    item = db.get(CalendarEventType, event_type_id)
    if not item:
        return RedirectResponse(url="/masters", status_code=303)
    item.is_active = False
    add_audit_log(db, "ui_archive_event_type", "calendar_event_type", item.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/event-types/{event_type_id}/delete")
def ui_delete_event_type(event_type_id: int, db: Session = Depends(get_db)):
    item = db.get(CalendarEventType, event_type_id)
    if not item:
        return RedirectResponse(url="/masters", status_code=303)
    db.delete(item)
    add_audit_log(db, "ui_delete_event_type", "calendar_event_type", item.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/departments/create")
def ui_create_department(
    name: str = Form(...),
    code: str = Form(...),
    display_order: int = Form(100),
    db: Session = Depends(get_db),
):
    department = Department(name=name, code=code, display_order=display_order)
    db.add(department)
    db.flush()
    add_audit_log(db, "ui_create_department", "department", department.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/departments/update")
def ui_update_department(
    department_id: int = Form(...),
    name: str = Form(...),
    code: str = Form(...),
    display_order: int = Form(100),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
):
    department = db.get(Department, department_id)
    if not department:
        return RedirectResponse(url="/masters", status_code=303)
    department.name = name
    department.code = code
    department.display_order = display_order
    department.is_active = is_active
    add_audit_log(db, "ui_update_department", "department", department.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/departments/{department_id}/archive")
def ui_archive_department(department_id: int, db: Session = Depends(get_db)):
    department = db.get(Department, department_id)
    if not department:
        return RedirectResponse(url="/masters", status_code=303)
    department.is_active = False
    add_audit_log(db, "ui_archive_department", "department", department.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/departments/{department_id}/delete")
def ui_delete_department(department_id: int, db: Session = Depends(get_db)):
    department = db.get(Department, department_id)
    if not department:
        return RedirectResponse(url="/masters", status_code=303)
    db.delete(department)
    add_audit_log(db, "ui_delete_department", "department", department.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/members/{member_id}/departments")
def ui_update_member_departments(member_id: int, department_ids: str = Form(...), db: Session = Depends(get_db)):
    member = db.get(CalendarMember, member_id)
    if not member:
        return RedirectResponse(url="/masters", status_code=303)

    existing = (
        db.query(CalendarMemberDepartment).filter(CalendarMemberDepartment.member_id == member_id).all()
    )
    for md in existing:
        db.delete(md)

    dept_id_list = [int(x) for x in department_ids.split(",") if x.strip()]
    for dept_id in dept_id_list:
        dept = db.get(Department, dept_id)
        if dept:
            md = CalendarMemberDepartment(member_id=member_id, department_id=dept_id)
            db.add(md)

    add_audit_log(db, "ui_update_member_departments", "calendar_member", member_id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/capacity-rules/create")
def ui_create_capacity_rule(
    event_type_id: int = Form(...),
    department_id: int = Form(0),
    day_type: str = Form(...),
    required_count: int = Form(...),
    db: Session = Depends(get_db),
):
    dept_id = department_id if department_id and department_id > 0 else None
    rule = CalendarEventTypeCapacityRule(
        event_type_id=event_type_id,
        department_id=dept_id,
        day_type=day_type,
        required_count=required_count,
    )
    db.add(rule)
    db.flush()
    add_audit_log(db, "ui_create_capacity_rule", "capacity_rule", rule.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/capacity-rules/update")
def ui_update_capacity_rule(
    rule_id: int = Form(...),
    event_type_id: int = Form(...),
    department_id: int = Form(0),
    day_type: str = Form(...),
    required_count: int = Form(...),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
):
    rule = db.get(CalendarEventTypeCapacityRule, rule_id)
    if not rule:
        return RedirectResponse(url="/masters", status_code=303)
    dept_id = department_id if department_id and department_id > 0 else None
    rule.event_type_id = event_type_id
    rule.department_id = dept_id
    rule.day_type = day_type
    rule.required_count = required_count
    rule.is_active = is_active
    add_audit_log(db, "ui_update_capacity_rule", "capacity_rule", rule.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/capacity-rules/{rule_id}/archive")
def ui_archive_capacity_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(CalendarEventTypeCapacityRule, rule_id)
    if not rule:
        return RedirectResponse(url="/masters", status_code=303)
    rule.is_active = False
    add_audit_log(db, "ui_archive_capacity_rule", "capacity_rule", rule.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/capacity-rules/{rule_id}/delete")
def ui_delete_capacity_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(CalendarEventTypeCapacityRule, rule_id)
    if not rule:
        return RedirectResponse(url="/masters", status_code=303)
    db.delete(rule)
    add_audit_log(db, "ui_delete_capacity_rule", "capacity_rule", rule.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/studios/create")
def ui_create_studio(
    name: str = Form(...),
    code: str = Form(...),
    display_order: int = Form(100),
    db: Session = Depends(get_db),
):
    studio = Studio(name=name, code=code, display_order=display_order)
    db.add(studio)
    db.flush()
    add_audit_log(db, "ui_create_studio", "studio", studio.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/studios/update")
def ui_update_studio(
    studio_id: int = Form(...),
    name: str = Form(...),
    code: str = Form(...),
    display_order: int = Form(100),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
):
    studio = db.get(Studio, studio_id)
    if not studio:
        return RedirectResponse(url="/masters", status_code=303)
    studio.name = name
    studio.code = code
    studio.display_order = display_order
    studio.is_active = is_active
    add_audit_log(db, "ui_update_studio", "studio", studio.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/studios/{studio_id}/archive")
def ui_archive_studio(studio_id: int, db: Session = Depends(get_db)):
    studio = db.get(Studio, studio_id)
    if not studio:
        return RedirectResponse(url="/masters", status_code=303)
    studio.is_active = False
    add_audit_log(db, "ui_archive_studio", "studio", studio.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/studios/{studio_id}/delete")
def ui_delete_studio(studio_id: int, db: Session = Depends(get_db)):
    studio = db.get(Studio, studio_id)
    if not studio:
        return RedirectResponse(url="/masters", status_code=303)
    db.delete(studio)
    add_audit_log(db, "ui_delete_studio", "studio", studio.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/programs/create")
def ui_create_program(
    name: str = Form(...),
    code: str = Form(...),
    short_label: str = Form(""),
    display_color: str = Form(""),
    display_order: int = Form(100),
    db: Session = Depends(get_db),
):
    program = Program(
        name=name,
        code=code,
        short_label=short_label or None,
        display_color=display_color or None,
        display_order=display_order,
    )
    db.add(program)
    db.flush()
    add_audit_log(db, "ui_create_program", "program", program.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/programs/update")
def ui_update_program(
    program_id: int = Form(...),
    name: str = Form(...),
    code: str = Form(...),
    short_label: str = Form(""),
    display_color: str = Form(""),
    display_order: int = Form(100),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
):
    program = db.get(Program, program_id)
    if not program:
        return RedirectResponse(url="/masters", status_code=303)
    program.name = name
    program.code = code
    program.short_label = short_label or None
    program.display_color = display_color or None
    program.display_order = display_order
    program.is_active = is_active
    add_audit_log(db, "ui_update_program", "program", program.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/programs/{program_id}/archive")
def ui_archive_program(program_id: int, db: Session = Depends(get_db)):
    program = db.get(Program, program_id)
    if not program:
        return RedirectResponse(url="/masters", status_code=303)
    program.is_active = False
    add_audit_log(db, "ui_archive_program", "program", program.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/programs/{program_id}/delete")
def ui_delete_program(program_id: int, db: Session = Depends(get_db)):
    program = db.get(Program, program_id)
    if not program:
        return RedirectResponse(url="/masters", status_code=303)
    db.delete(program)
    add_audit_log(db, "ui_delete_program", "program", program.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/events/create")
def ui_create_event(
    request: Request,
    member_id: int = Form(...),
    event_date: date = Form(...),
    title: str = Form(...),
    event_type_id: str | None = Form(None),
    memo: str = Form(""),
    db: Session = Depends(get_db),
):
    member = db.get(CalendarMember, member_id)
    if not member:
        return RedirectResponse(url="/calendar", status_code=303)

    # Convert empty string to None, then to int if provided
    event_type_id_int = None
    if event_type_id and event_type_id.strip():
        try:
            event_type_id_int = int(event_type_id)
        except ValueError:
            return RedirectResponse(url="/calendar", status_code=303)

    # Check event_type existence only if provided
    event_type = None
    if event_type_id_int:
        event_type = db.get(CalendarEventType, event_type_id_int)
        if not event_type:
            return RedirectResponse(url="/calendar", status_code=303)

    # Check for duplicate events
    if event_type_id_int:
        existing = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.member_id == member_id,
                CalendarEvent.event_date == event_date,
                CalendarEvent.event_type_id == event_type_id_int,
                CalendarEvent.is_archived == False,
            )
            .first()
        )
        if existing:
            return RedirectResponse(url="/calendar", status_code=303)
    else:
        existing = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.member_id == member_id,
                CalendarEvent.event_date == event_date,
                CalendarEvent.title == title,
                CalendarEvent.is_archived == False,
            )
            .first()
        )
        if existing:
            return RedirectResponse(url="/calendar", status_code=303)

    # Capacity check if required and event_type is provided
    if event_type and event_type.requires_capacity_check and event_date:
        capacity_check_result = check_capacity(db, event_date, event_type_id_int)
        if not capacity_check_result["sufficient"]:
            return RedirectResponse(url="/calendar", status_code=303)

    event = CalendarEvent(
        member_id=member_id,
        event_date=event_date,
        event_type_id=event_type_id_int,
        title=title,
        display_label=title,
        memo=memo,
    )
    db.add(event)
    db.flush()
    add_audit_log(db, "ui_create_event", "calendar_event", event.id)
    db.commit()
    return RedirectResponse(url="/calendar", status_code=303)


@router.post("/ui/events/{event_id}/edit")
def ui_edit_event(
    event_id: int,
    request: Request,
    member_id: int = Form(...),
    event_date: date = Form(...),
    title: str = Form(...),
    event_type_id: str | None = Form(None),
    memo: str = Form(""),
    db: Session = Depends(get_db),
):
    event = db.get(CalendarEvent, event_id)
    if not event:
        return RedirectResponse(url="/calendar", status_code=303)

    member = db.get(CalendarMember, member_id)
    if not member:
        return RedirectResponse(url="/calendar", status_code=303)

    # Convert empty string to None, then to int if provided
    event_type_id_int = None
    if event_type_id and event_type_id.strip():
        try:
            event_type_id_int = int(event_type_id)
        except ValueError:
            return RedirectResponse(url="/calendar", status_code=303)

    # Check event_type existence only if provided
    event_type = None
    if event_type_id_int:
        event_type = db.get(CalendarEventType, event_type_id_int)
        if not event_type:
            return RedirectResponse(url="/calendar", status_code=303)

    # Check for duplicate events (excluding current event)
    if event_type_id_int:
        existing = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.member_id == member_id,
                CalendarEvent.event_date == event_date,
                CalendarEvent.event_type_id == event_type_id_int,
                CalendarEvent.is_archived == False,
                CalendarEvent.id != event_id,
            )
            .first()
        )
        if existing:
            return RedirectResponse(url="/calendar", status_code=303)
    else:
        existing = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.member_id == member_id,
                CalendarEvent.event_date == event_date,
                CalendarEvent.title == title,
                CalendarEvent.is_archived == False,
                CalendarEvent.id != event_id,
            )
            .first()
        )
        if existing:
            return RedirectResponse(url="/calendar", status_code=303)

    # Capacity check if required and event_type is provided
    if event_type and event_type.requires_capacity_check and event_date:
        capacity_check_result = check_capacity(db, event_date, event_type_id_int)
        if not capacity_check_result["sufficient"]:
            return RedirectResponse(url="/calendar", status_code=303)

    # Update the event
    event.member_id = member_id
    event.event_date = event_date
    event.event_type_id = event_type_id_int
    event.title = title
    event.display_label = title
    event.memo = memo

    add_audit_log(db, "ui_edit_event", "calendar_event", event.id)
    db.commit()
    return RedirectResponse(url="/calendar", status_code=303)


@router.post("/ui/events/{event_id}/delete")
def ui_delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(CalendarEvent, event_id)
    if not event:
        return RedirectResponse(url="/calendar", status_code=303)

    db.delete(event)
    add_audit_log(db, "ui_delete_event", "calendar_event", event_id)
    db.commit()
    return RedirectResponse(url="/calendar", status_code=303)


@router.post("/ui/program-schedules/create")
def ui_create_program_schedule(
    program_id: str = Form(""),
    program_name: str = Form(""),
    studio_id: int = Form(...),
    event_date: date = Form(...),
    db: Session = Depends(get_db),
):
    # Handle program selection (dropdown or free text)
    program = None
    if program_id and program_id.strip():
        try:
            program_id_int = int(program_id)
            program = db.get(Program, program_id_int)
        except ValueError:
            return RedirectResponse(url="/calendar", status_code=303)
    elif program_name and program_name.strip():
        # Auto-create program if not found
        program = (
            db.query(Program)
            .filter(Program.name == program_name)
            .first()
        )
        if not program:
            program = Program(
                name=program_name,
                code=program_name[:50],
                short_label=program_name[:50],
                is_active=True,
                display_order=100,
            )
            db.add(program)
            db.flush()
            add_audit_log(db, "ui_auto_create_program", "program", program.id)
    
    if not program:
        return RedirectResponse(url="/calendar", status_code=303)

    studio = db.get(Studio, studio_id)
    if not studio:
        return RedirectResponse(url="/calendar", status_code=303)

    # Check for duplicate schedules
    existing = (
        db.query(ProgramSchedule)
        .filter(
            ProgramSchedule.program_id == program.id,
            ProgramSchedule.studio_id == studio_id,
            ProgramSchedule.event_date == event_date,
        )
        .first()
    )
    if existing:
        return RedirectResponse(url="/calendar", status_code=303)

    # Create the schedule
    schedule = ProgramSchedule(
        program_id=program.id,
        studio_id=studio_id,
        event_date=event_date,
    )
    db.add(schedule)
    db.flush()
    add_audit_log(db, "ui_create_program_schedule", "program_schedule", schedule.id)
    db.commit()
    return RedirectResponse(url="/calendar", status_code=303)


@router.post("/ui/program-schedules/edit")
def ui_edit_program_schedule(
    schedule_id: int,
    program_id: str = Form(""),
    program_name: str = Form(""),
    studio_id: int = Form(...),
    event_date: date = Form(...),
    db: Session = Depends(get_db),
):
    schedule = db.get(ProgramSchedule, schedule_id)
    if not schedule:
        return RedirectResponse(url="/calendar", status_code=303)

    # Handle program selection (dropdown or free text)
    program = None
    if program_id and program_id.strip():
        try:
            program_id_int = int(program_id)
            program = db.get(Program, program_id_int)
        except ValueError:
            return RedirectResponse(url="/calendar", status_code=303)
    elif program_name and program_name.strip():
        # Auto-create program if not found
        program = (
            db.query(Program)
            .filter(Program.name == program_name)
            .first()
        )
        if not program:
            program = Program(
                name=program_name,
                code=program_name[:50],
                short_label=program_name[:50],
                is_active=True,
                display_order=100,
            )
            db.add(program)
            db.flush()
            add_audit_log(db, "ui_auto_create_program", "program", program.id)
    
    if not program:
        return RedirectResponse(url="/calendar", status_code=303)

    studio = db.get(Studio, studio_id)
    if not studio:
        return RedirectResponse(url="/calendar", status_code=303)

    # Check for duplicate schedules (excluding current schedule)
    existing = (
        db.query(ProgramSchedule)
        .filter(
            ProgramSchedule.program_id == program.id,
            ProgramSchedule.studio_id == studio_id,
            ProgramSchedule.event_date == event_date,
            ProgramSchedule.id != schedule_id,
        )
        .first()
    )
    if existing:
        return RedirectResponse(url="/calendar", status_code=303)

    # Update the schedule
    schedule.program_id = program.id
    schedule.studio_id = studio_id
    schedule.event_date = event_date

    add_audit_log(db, "ui_edit_program_schedule", "program_schedule", schedule.id)
    db.commit()
    return RedirectResponse(url="/calendar", status_code=303)


@router.post("/ui/program-schedules/{schedule_id}/delete")
def ui_delete_program_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.get(ProgramSchedule, schedule_id)
    if not schedule:
        return RedirectResponse(url="/calendar", status_code=303)

    db.delete(schedule)
    add_audit_log(db, "ui_delete_program_schedule", "program_schedule", schedule_id)
    db.commit()
    return RedirectResponse(url="/calendar", status_code=303)


@router.post("/ui/regular-schedules/create")
def ui_create_regular_schedule(
    name: str = Form(...),
    program_id: int = Form(...),
    studio_id: int = Form(...),
    day_of_week: int = Form(...),
    display_order: int = Form(100),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
):
    program = db.get(Program, program_id)
    if not program:
        return RedirectResponse(url="/masters", status_code=303)

    studio = db.get(Studio, studio_id)
    if not studio:
        return RedirectResponse(url="/masters", status_code=303)

    regular_schedule = RegularSchedule(
        name=name,
        program_id=program_id,
        studio_id=studio_id,
        day_of_week=day_of_week,
        display_order=display_order,
        is_active=is_active,
    )
    db.add(regular_schedule)
    db.flush()
    add_audit_log(db, "ui_create_regular_schedule", "regular_schedule", regular_schedule.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/regular-schedules/update")
def ui_update_regular_schedule(
    regular_schedule_id: int = Form(...),
    name: str = Form(...),
    program_id: int = Form(...),
    studio_id: int = Form(...),
    day_of_week: int = Form(...),
    display_order: int = Form(100),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
):
    regular_schedule = db.get(RegularSchedule, regular_schedule_id)
    if not regular_schedule:
        return RedirectResponse(url="/masters", status_code=303)

    program = db.get(Program, program_id)
    if not program:
        return RedirectResponse(url="/masters", status_code=303)

    studio = db.get(Studio, studio_id)
    if not studio:
        return RedirectResponse(url="/masters", status_code=303)

    regular_schedule.name = name
    regular_schedule.program_id = program_id
    regular_schedule.studio_id = studio_id
    regular_schedule.day_of_week = day_of_week
    regular_schedule.display_order = display_order
    regular_schedule.is_active = is_active

    add_audit_log(db, "ui_update_regular_schedule", "regular_schedule", regular_schedule.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/regular-schedules/{regular_schedule_id}/archive")
def ui_archive_regular_schedule(regular_schedule_id: int, db: Session = Depends(get_db)):
    regular_schedule = db.get(RegularSchedule, regular_schedule_id)
    if not regular_schedule:
        return RedirectResponse(url="/masters", status_code=303)

    regular_schedule.is_active = False
    add_audit_log(db, "ui_archive_regular_schedule", "regular_schedule", regular_schedule_id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/regular-schedules/{regular_schedule_id}/delete")
def ui_delete_regular_schedule(regular_schedule_id: int, db: Session = Depends(get_db)):
    regular_schedule = db.get(RegularSchedule, regular_schedule_id)
    if not regular_schedule:
        return RedirectResponse(url="/masters", status_code=303)

    db.delete(regular_schedule)
    add_audit_log(db, "ui_delete_regular_schedule", "regular_schedule", regular_schedule_id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)


@router.post("/ui/regular-schedules/apply")
def ui_apply_regular_schedule(
    regular_schedule_id: int = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(get_db),
):
    regular_schedule = db.get(RegularSchedule, regular_schedule_id)
    if not regular_schedule:
        return RedirectResponse(url="/calendar", status_code=303)

    # Get all days in the month
    from datetime import datetime, timedelta
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    # Apply regular schedule to matching days
    current_date = start_date
    while current_date <= end_date:
        # day_of_week: 0=Monday, 4=Friday
        # Python weekday(): 0=Monday, 6=Sunday
        if current_date.weekday() == regular_schedule.day_of_week:
            # Check if schedule already exists for this day/studio
            existing = (
                db.query(ProgramSchedule)
                .filter(
                    ProgramSchedule.program_id == regular_schedule.program_id,
                    ProgramSchedule.studio_id == regular_schedule.studio_id,
                    ProgramSchedule.event_date == current_date,
                )
                .first()
            )
            if not existing:
                new_schedule = ProgramSchedule(
                    program_id=regular_schedule.program_id,
                    studio_id=regular_schedule.studio_id,
                    event_date=current_date,
                )
                db.add(new_schedule)
                db.flush()
                add_audit_log(db, "ui_apply_regular_schedule", "program_schedule", new_schedule.id)
        current_date += timedelta(days=1)

    db.commit()
    return RedirectResponse(url=f"/calendar?year={year}&month={month}", status_code=303)
