import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Program
from ..schemas import ProgramCreate, ProgramUpdate, success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/calendar/programs")
def list_programs(db: Session = Depends(get_db)):
    programs = db.query(Program).order_by(Program.display_order, Program.id).all()
    return success([{
        "id": p.id,
        "name": p.name,
        "code": p.code,
        "short_label": p.short_label,
        "display_color": p.display_color,
        "is_active": p.is_active,
        "display_order": p.display_order,
    } for p in programs], "番組一覧を取得しました")

@router.post("/api/calendar/programs")
def create_program(payload: ProgramCreate, db: Session = Depends(get_db)):
    program = Program(**payload.model_dump())
    db.add(program)
    db.flush()
    add_audit_log(db, "create_program", "program", program.id, request=payload.model_dump())
    db.commit()
    return success({"id": program.id}, "番組を作成しました")

@router.put("/api/calendar/programs/{program_id}")
def update_program(program_id: int, payload: ProgramUpdate, db: Session = Depends(get_db)):
    program = db.get(Program, program_id)
    if not program:
        return error("PROGRAM_NOT_FOUND", "番組が見つかりません")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(program, key, value)
    add_audit_log(db, "update_program", "program", program.id, request=payload.model_dump(exclude_unset=True))
    db.commit()
    return success({"id": program.id}, "番組を更新しました")

@router.post("/api/calendar/programs/{program_id}/archive")
def archive_program(program_id: int, db: Session = Depends(get_db)):
    program = db.get(Program, program_id)
    if not program:
        return error("PROGRAM_NOT_FOUND", "番組が見つかりません")
    program.is_active = False
    add_audit_log(db, "archive_program", "program", program.id)
    db.commit()
    return success({"id": program.id}, "番組を無効化しました")
