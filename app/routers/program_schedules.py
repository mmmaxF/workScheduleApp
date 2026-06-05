import logging
from datetime import date
from calendar import monthrange
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Program, Studio, ProgramSchedule
from ..schemas import ProgramScheduleCreate, ProgramScheduleBulkCreate, success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/calendar/program-schedules")
def list_program_schedules(year: int, month: int, db: Session = Depends(get_db)):
    last_day = monthrange(year, month)[1]
    schedules = db.query(ProgramSchedule).filter(
        ProgramSchedule.event_date >= date(year, month, 1),
        ProgramSchedule.event_date <= date(year, month, last_day),
    ).all()
    return success([{
        "id": s.id,
        "program_id": s.program_id,
        "program_name": s.program.name if s.program else None,
        "program_short_label": s.program.short_label if s.program else None,
        "program_display_color": s.program.display_color if s.program else None,
        "studio_id": s.studio_id,
        "studio_name": s.studio.name if s.studio else None,
        "event_date": s.event_date.isoformat(),
    } for s in schedules], "番組スケジュール一覧を取得しました")

@router.post("/api/calendar/program-schedules")
def create_program_schedule(payload: ProgramScheduleCreate, db: Session = Depends(get_db)):
    if not db.get(Program, payload.program_id):
        return error("PROGRAM_NOT_FOUND", "番組が見つかりません")
    if not db.get(Studio, payload.studio_id):
        return error("STUDIO_NOT_FOUND", "スタジオが見つかりません")
    
    schedule = ProgramSchedule(**payload.model_dump())
    db.add(schedule)
    db.flush()
    add_audit_log(db, "create_program_schedule", "program_schedule", schedule.id, request=payload.model_dump())
    db.commit()
    return success({"id": schedule.id}, "番組スケジュールを作成しました")

@router.delete("/api/calendar/program-schedules/{schedule_id}")
def delete_program_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.get(ProgramSchedule, schedule_id)
    if not schedule:
        return error("PROGRAM_SCHEDULE_NOT_FOUND", "番組スケジュールが見つかりません")
    db.delete(schedule)
    add_audit_log(db, "delete_program_schedule", "program_schedule", schedule_id)
    db.commit()
    return success({"id": schedule_id}, "番組スケジュールを削除しました")

@router.post("/api/calendar/program-schedules/bulk")
def create_program_schedules_bulk(payload: ProgramScheduleBulkCreate, db: Session = Depends(get_db)):
    success_count = 0
    error_count = 0
    errors = []
    created_ids = []

    for idx, schedule_data in enumerate(payload.schedules):
        try:
            # Resolve program_id from program_name if not provided
            program_id = schedule_data.program_id
            if program_id is None and schedule_data.program_name:
                program = db.query(Program).filter(
                    Program.name == schedule_data.program_name,
                    Program.is_active == True
                ).first()
                if not program:
                    errors.append({
                        "index": idx,
                        "error": "PROGRAM_NOT_FOUND",
                        "message": f"番組名 '{schedule_data.program_name}' が見つかりません",
                        "data": schedule_data.model_dump()
                    })
                    error_count += 1
                    continue
                program_id = program.id
            elif program_id is None:
                errors.append({
                    "index": idx,
                    "error": "PROGRAM_REQUIRED",
                    "message": "program_id または program_name のいずれかを指定してください",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            program = db.get(Program, program_id)
            if not program:
                errors.append({
                    "index": idx,
                    "error": "PROGRAM_NOT_FOUND",
                    "message": f"番組ID {program_id} が見つかりません",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            # Resolve studio_id from studio_name if not provided
            studio_id = schedule_data.studio_id
            if studio_id is None and schedule_data.studio_name:
                studio = db.query(Studio).filter(
                    Studio.name == schedule_data.studio_name,
                    Studio.is_active == True
                ).first()
                if not studio:
                    errors.append({
                        "index": idx,
                        "error": "STUDIO_NOT_FOUND",
                        "message": f"スタジオ名 '{schedule_data.studio_name}' が見つかりません",
                        "data": schedule_data.model_dump()
                    })
                    error_count += 1
                    continue
                studio_id = studio.id
            elif studio_id is None:
                errors.append({
                    "index": idx,
                    "error": "STUDIO_REQUIRED",
                    "message": "studio_id または studio_name のいずれかを指定してください",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            studio = db.get(Studio, studio_id)
            if not studio:
                errors.append({
                    "index": idx,
                    "error": "STUDIO_NOT_FOUND",
                    "message": f"スタジオID {studio_id} が見つかりません",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            # Check for duplicate schedules
            existing = db.query(ProgramSchedule).filter(
                ProgramSchedule.program_id == program_id,
                ProgramSchedule.studio_id == studio_id,
                ProgramSchedule.event_date == schedule_data.event_date,
            ).first()
            if existing:
                errors.append({
                    "index": idx,
                    "error": "DUPLICATE_SCHEDULE",
                    "message": "同一番組・同一スタジオ・同日のスケジュールが既に存在します",
                    "data": schedule_data.model_dump()
                })
                error_count += 1
                continue

            schedule = ProgramSchedule(
                program_id=program_id,
                studio_id=studio_id,
                event_date=schedule_data.event_date
            )
            db.add(schedule)
            db.flush()
            add_audit_log(db, "create_program_schedule_bulk", "program_schedule", schedule.id, request=schedule_data.model_dump())
            created_ids.append(schedule.id)
            success_count += 1

        except Exception as e:
            errors.append({
                "index": idx,
                "error": "INTERNAL_ERROR",
                "message": str(e),
                "data": schedule_data.model_dump()
            })
            error_count += 1

    db.commit()

    return success({
        "success_count": success_count,
        "error_count": error_count,
        "created_ids": created_ids,
        "errors": errors
    }, f"バルクインポート完了: 成功 {success_count}件, 失敗 {error_count}件")
