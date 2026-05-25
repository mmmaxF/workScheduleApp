import logging
from datetime import date
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .logging_config import setup_logging
from .models import CalendarMember, CalendarEventType, CalendarEventDraft
from .routers import router
from .services import build_monthly_calendar, validate_draft, approve_draft, add_audit_log

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Headless Calendar Step 1", version="0.1.0")

Base.metadata.create_all(bind=engine)

app.include_router(router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def seed_initial_data(db: Session):
    if db.query(CalendarEventType).count() == 0:
        defaults = [
            {"code": "rd", "name": "RD", "short_label": "RD", "display_color": "#dbeafe", "is_work_assignment": True, "requires_capacity_check": True, "display_order": 1},
            {"code": "annual_leave", "name": "年休", "short_label": "年休", "display_color": "#fee2e2", "is_leave": True, "display_order": 2},
            {"code": "manager_meeting", "name": "部長会", "short_label": "部長会", "display_color": "#fef3c7", "display_order": 3},
            {"code": "vehicle_meeting", "name": "車両会議", "short_label": "車両会議", "display_color": "#dcfce7", "display_order": 4},
            {"code": "star_one", "name": "★", "short_label": "★", "display_symbol": "★", "display_color": "#f5d0fe", "display_order": 5},
            {"code": "star_two", "name": "★★", "short_label": "★★", "display_symbol": "★★", "display_color": "#e9d5ff", "display_order": 6},
        ]
        for item in defaults:
            db.add(CalendarEventType(**item))
        db.commit()
        logger.info("seeded default event types")

@app.on_event("startup")
def on_startup():
    db = next(get_db())
    try:
        seed_initial_data(db)
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def index():
    return RedirectResponse(url="/calendar")

@app.get("/calendar", response_class=HTMLResponse)
def calendar_page(request: Request, year: int | None = None, month: int | None = None, db: Session = Depends(get_db)):
    today = date.today()
    year = year or today.year
    month = month or today.month
    data = build_monthly_calendar(db, year, month)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    members = db.query(CalendarMember).filter(CalendarMember.is_active == True).order_by(CalendarMember.display_order, CalendarMember.id).all()
    event_types = db.query(CalendarEventType).filter(CalendarEventType.is_active == True).order_by(CalendarEventType.display_order, CalendarEventType.id).all()
    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "calendar": data,
        "members": members,
        "event_types": event_types,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    })

@app.post("/ui/drafts/create")
def ui_create_draft(
    member_id: int = Form(...),
    event_date: date = Form(...),
    event_type_id: int = Form(...),
    memo: str = Form(""),
    db: Session = Depends(get_db),
):
    event_type = db.get(CalendarEventType, event_type_id)
    member = db.get(CalendarMember, member_id)
    title = event_type.name if event_type else "予定"
    draft = CalendarEventDraft(
        member_name_raw=member.display_name if member else None,
        member_id=member_id,
        event_date=event_date,
        event_type_name_raw=event_type.name if event_type else None,
        event_type_id=event_type_id,
        title=title,
        display_label=event_type.short_label if event_type else title,
        memo=memo,
        source_type="manual",
        source_text="Web UIから作成",
    )
    db.add(draft)
    db.flush()
    add_audit_log(db, "ui_create_draft", "calendar_event_draft", draft.id)
    db.commit()
    return RedirectResponse(url="/drafts", status_code=303)

@app.get("/masters", response_class=HTMLResponse)
def masters_page(request: Request, db: Session = Depends(get_db)):
    members = db.query(CalendarMember).order_by(CalendarMember.display_order, CalendarMember.id).all()
    event_types = db.query(CalendarEventType).order_by(CalendarEventType.display_order, CalendarEventType.id).all()
    return templates.TemplateResponse("masters.html", {"request": request, "members": members, "event_types": event_types})

@app.post("/ui/members/create")
def ui_create_member(display_name: str = Form(...), short_name: str = Form(""), display_order: int = Form(100), db: Session = Depends(get_db)):
    member = CalendarMember(display_name=display_name, short_name=short_name or None, display_order=display_order)
    db.add(member)
    db.flush()
    add_audit_log(db, "ui_create_member", "calendar_member", member.id)
    db.commit()
    return RedirectResponse(url="/masters", status_code=303)

@app.post("/ui/event-types/create")
def ui_create_event_type(
    code: str = Form(...),
    name: str = Form(...),
    short_label: str = Form(""),
    display_color: str = Form(""),
    is_leave: bool = Form(False),
    is_work_assignment: bool = Form(False),
    requires_capacity_check: bool = Form(False),
    display_order: int = Form(100),
    db: Session = Depends(get_db),
):
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

@app.get("/drafts", response_class=HTMLResponse)
def drafts_page(request: Request, db: Session = Depends(get_db)):
    drafts = db.query(CalendarEventDraft).order_by(CalendarEventDraft.id.desc()).all()
    return templates.TemplateResponse("drafts.html", {"request": request, "drafts": drafts})

@app.post("/ui/drafts/{draft_id}/validate")
def ui_validate_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.get(CalendarEventDraft, draft_id)
    if draft:
        validate_draft(db, draft)
        db.commit()
    return RedirectResponse(url="/drafts", status_code=303)

@app.post("/ui/drafts/{draft_id}/approve")
def ui_approve_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.get(CalendarEventDraft, draft_id)
    if draft and draft.approval_status != "approved":
        try:
            approve_draft(db, draft)
            db.commit()
        except Exception as exc:
            logger.exception("approve failed: %s", exc)
            db.rollback()
    return RedirectResponse(url="/drafts", status_code=303)

@app.post("/ui/drafts/{draft_id}/reject")
def ui_reject_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.get(CalendarEventDraft, draft_id)
    if draft:
        draft.approval_status = "rejected"
        add_audit_log(db, "ui_reject_draft", "calendar_event_draft", draft.id)
        db.commit()
    return RedirectResponse(url="/drafts", status_code=303)
