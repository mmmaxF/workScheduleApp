import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .logging_config import setup_logging
from .models import CalendarEventType, Department, CalendarMember, Studio, Program
from .routers.members import router as members_router
from .routers.event_types import router as event_types_router
from .routers.events import router as events_router
from .routers.departments import router as departments_router
from .routers.capacity_rules import router as capacity_rules_router
from .routers.studios import router as studios_router
from .routers.programs import router as programs_router
from .routers.program_schedules import router as program_schedules_router
from .routers.history import router as history_router
from .routers.search import router as search_router
from .routers.dev import router as dev_router
from .routers.ai import router as ai_router
from .routers.chat import router as chat_router
from .csv.csv_router import router as csv_router
from .ui.router import router as ui_router

load_dotenv()

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Headless Calendar Step 1", version="0.1.0")

Base.metadata.create_all(bind=engine)

# Include all routers
app.include_router(members_router)
app.include_router(event_types_router)
app.include_router(events_router)
app.include_router(departments_router)
app.include_router(capacity_rules_router)
app.include_router(studios_router)
app.include_router(programs_router)
app.include_router(program_schedules_router)
app.include_router(history_router)
app.include_router(search_router)
app.include_router(dev_router)
app.include_router(ai_router)
app.include_router(chat_router)
app.include_router(csv_router)
app.include_router(ui_router)
app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")

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

    if db.query(Department).count() == 0:
        dept_defaults = [
            {"name": "映像", "code": "video", "display_order": 1},
            {"name": "音声", "code": "audio", "display_order": 2},
            {"name": "調整", "code": "adjustment", "display_order": 3},
            {"name": "照明", "code": "lighting", "display_order": 4},
            {"name": "回線", "code": "line", "display_order": 5},
        ]
        for item in dept_defaults:
            db.add(Department(**item))
        db.commit()
        logger.info("seeded default departments")

    if db.query(CalendarMember).count() == 0:
        member_defaults = [
            {"display_name": "田中太郎", "short_name": "田中", "display_order": 1},
            {"display_name": "山田花子", "short_name": "山田", "display_order": 2},
            {"display_name": "佐藤次郎", "short_name": "佐藤", "display_order": 3},
        ]
        for item in member_defaults:
            db.add(CalendarMember(**item))
        db.commit()
        logger.info("seeded default members")

    if db.query(Studio).count() == 0:
        studio_defaults = [
            {"name": "スタジオA", "code": "studio_a", "display_order": 1},
            {"name": "スタジオB", "code": "studio_b", "display_order": 2},
            {"name": "スタジオC", "code": "studio_c", "display_order": 3},
        ]
        for item in studio_defaults:
            db.add(Studio(**item))
        db.commit()
        logger.info("seeded default studios")

    if db.query(Program).count() == 0:
        program_defaults = [
            {"name": "ニュース番組", "code": "news", "short_label": "ニュース", "display_color": "#dbeafe", "display_order": 1},
            {"name": "情報番組", "code": "info", "short_label": "情報", "display_color": "#dcfce7", "display_order": 2},
            {"name": "バラエティ", "code": "variety", "short_label": "バラエティ", "display_color": "#fef3c7", "display_order": 3},
        ]
        for item in program_defaults:
            db.add(Program(**item))
        db.commit()
        logger.info("seeded default programs")


@app.on_event("startup")
def on_startup():
    db = next(get_db())
    try:
        seed_initial_data(db)
    finally:
        db.close()
