# app/csv_router.py
"""
CSVインポート／エクスポート用API。

方針:
- CSV解析処理そのものはDBを直接更新しない。
- preview API はCSVをJSON化して検証するだけ。
- execute API は、JSON化されたvalid行だけを既存の登録ロジック相当で反映する。
- events のCSVインポートは正式予定 calendar_events へ直接入れず、
  calendar_event_drafts に保存する。
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import extract
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    CalendarMember,
    CalendarEventType,
    CalendarEventDraft,
    CalendarEvent,
    Program,
    ProgramSchedule,
    Studio,
)
from ..schemas import success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()


# =========================================================
# 定数
# =========================================================

IMPORT_MEMBERS = "members"
IMPORT_EVENT_TYPES = "event_types"
IMPORT_EVENTS = "events"
IMPORT_PROGRAMS = "programs"
IMPORT_PROGRAM_SCHEDULES = "program_schedules"

SUPPORTED_IMPORT_TYPES = {
    IMPORT_MEMBERS,
    IMPORT_EVENT_TYPES,
    IMPORT_EVENTS,
    IMPORT_PROGRAMS,
    IMPORT_PROGRAM_SCHEDULES,
}

SUPPORTED_EXPORT_TYPES = {
    IMPORT_MEMBERS,
    IMPORT_EVENT_TYPES,
    IMPORT_EVENTS,
    IMPORT_PROGRAMS,
    IMPORT_PROGRAM_SCHEDULES,
    "monthly",
}

REQUIRED_HEADERS = {
    IMPORT_MEMBERS: [
        "display_name",
        "short_name",
        "departments",
        "is_active",
        "display_order",
    ],
    IMPORT_EVENT_TYPES: [
        "code",
        "name",
        "short_label",
        "display_color",
        "display_symbol",
        "is_leave",
        "is_work_assignment",
        "requires_capacity_check",
        "is_active",
        "display_order",
    ],
    IMPORT_EVENTS: [
        "member_name",
        "event_date",
        "title",
        "event_type_name",
        "department_name",
        "display_label",
        "memo",
    ],
    IMPORT_PROGRAMS: [
        "program_name",
        "short_label",
        "display_color",
        "is_active",
        "display_order",
    ],
    IMPORT_PROGRAM_SCHEDULES: [
        "program_name",
        "studio_name",
        "event_date",
    ],
}


# =========================================================
# Pydantic
# =========================================================

class CsvExecutePayload(BaseModel):
    import_type: str
    rows: List[Dict[str, Any]]
    mode: str = "append"  # "append" (追加) or "replace" (上書き)


# =========================================================
# 共通ユーティリティ
# =========================================================

def model_kwargs(model_class: Any, values: Dict[str, Any]) -> Dict[str, Any]:
    """
    SQLAlchemyモデルに存在するカラムだけを抽出する。

    モデル定義に存在しないキーを渡してエラーになるのを防ぐ。
    """
    column_names = {column.name for column in model_class.__table__.columns}
    return {k: v for k, v in values.items() if k in column_names}


def decode_csv_bytes(file_bytes: bytes) -> str:
    """
    CSV bytes を文字列へ変換する。

    対応:
    - UTF-8 BOM
    - UTF-8
    - CP932
    - Shift_JIS
    """
    encodings = ["utf-8-sig", "utf-8", "cp932", "shift_jis"]

    last_error: Optional[Exception] = None

    for enc in encodings:
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise ValueError(f"CSVの文字コードを判定できませんでした: {last_error}")


def normalize_header(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_bool(value: Any) -> Optional[bool]:
    text = normalize_cell(value).lower()

    if text in {"true", "1", "yes", "y", "有効", "はい"}:
        return True

    if text in {"false", "0", "no", "n", "無効", "いいえ"}:
        return False

    return None


def parse_int(value: Any) -> Optional[int]:
    text = normalize_cell(value)

    if text == "":
        return None

    try:
        return int(text)
    except ValueError:
        return None


def parse_date(value: Any) -> Optional[date]:
    text = normalize_cell(value)

    # Try various date formats
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y/%-m/%-d"]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def read_csv_rows(file_bytes: bytes) -> List[Dict[str, str]]:
    """
    CSVファイルを読み、ヘッダー名を正規化したdict配列へ変換する。
    """
    text = decode_csv_bytes(file_bytes)
    stream = io.StringIO(text, newline="")

    reader = csv.DictReader(stream)

    if reader.fieldnames is None:
        raise ValueError("CSVヘッダーが見つかりません。")

    rows: List[Dict[str, str]] = []

    for raw_row in reader:
        row: Dict[str, str] = {}

        for key, value in raw_row.items():
            row[normalize_header(key)] = normalize_cell(value)

        rows.append(row)

    return rows


def make_row_result(
    row_number: int,
    data: Dict[str, Any],
    errors: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "row_number": row_number,
        "status": "invalid" if errors else "valid",
        "data": data,
        "errors": errors,
    }


def validate_headers(import_type: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []

    if import_type not in SUPPORTED_IMPORT_TYPES:
        return [{
            "field": "import_type",
            "error_code": "UNSUPPORTED_IMPORT_TYPE",
            "message": f"未対応のimport_typeです: {import_type}",
        }]

    if not rows:
        return [{
            "field": "file",
            "error_code": "EMPTY_CSV",
            "message": "CSVにデータ行がありません。",
        }]

    headers = set(rows[0].keys())

    for required in REQUIRED_HEADERS[import_type]:
        if required not in headers:
            errors.append({
                "field": required,
                "error_code": "REQUIRED_HEADER_MISSING",
                "message": f"必須ヘッダーがありません: {required}",
            })

    return errors


# =========================================================
# 行バリデーション
# =========================================================

def validate_member_row(row_number: int, row: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []

    display_name = normalize_cell(row.get("display_name"))
    short_name = normalize_cell(row.get("short_name"))
    is_active = parse_bool(row.get("is_active"))
    display_order = parse_int(row.get("display_order"))

    if not display_name:
        errors.append({
            "field": "display_name",
            "error_code": "REQUIRED",
            "message": "display_name は必須です。",
        })

    if is_active is None:
        errors.append({
            "field": "is_active",
            "error_code": "INVALID_BOOLEAN",
            "message": "is_active は true / false で指定してください。",
        })

    if display_order is None:
        errors.append({
            "field": "display_order",
            "error_code": "INVALID_INTEGER",
            "message": "display_order は整数で指定してください。",
        })

    data = {
        "display_name": display_name,
        "short_name": short_name,
        "is_active": is_active,
        "display_order": display_order,
    }

    return make_row_result(row_number, data, errors)


def validate_event_type_row(row_number: int, row: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []

    code = normalize_cell(row.get("code"))
    name = normalize_cell(row.get("name"))
    short_label = normalize_cell(row.get("short_label")) or name
    display_color = normalize_cell(row.get("display_color"))
    display_symbol = normalize_cell(row.get("display_symbol"))

    is_leave = parse_bool(row.get("is_leave"))
    is_work_assignment = parse_bool(row.get("is_work_assignment"))
    requires_capacity_check = parse_bool(row.get("requires_capacity_check"))
    is_active = parse_bool(row.get("is_active"))
    display_order = parse_int(row.get("display_order"))

    if not code:
        errors.append({
            "field": "code",
            "error_code": "REQUIRED",
            "message": "code は必須です。",
        })

    if not name:
        errors.append({
            "field": "name",
            "error_code": "REQUIRED",
            "message": "name は必須です。",
        })

    for field_name, parsed_value in [
        ("is_leave", is_leave),
        ("is_work_assignment", is_work_assignment),
        ("requires_capacity_check", requires_capacity_check),
        ("is_active", is_active),
    ]:
        if parsed_value is None:
            errors.append({
                "field": field_name,
                "error_code": "INVALID_BOOLEAN",
                "message": f"{field_name} は true / false で指定してください。",
            })

    if display_order is None:
        errors.append({
            "field": "display_order",
            "error_code": "INVALID_INTEGER",
            "message": "display_order は整数で指定してください。",
        })

    data = {
        "code": code,
        "name": name,
        "short_label": short_label,
        "display_color": display_color,
        "display_symbol": display_symbol,
        "is_leave": is_leave,
        "is_work_assignment": is_work_assignment,
        "requires_capacity_check": requires_capacity_check,
        "is_active": is_active,
        "display_order": display_order,
    }

    return make_row_result(row_number, data, errors)


def validate_program_row(row_number: int, row: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []

    program_name = normalize_cell(row.get("program_name"))
    short_label = normalize_cell(row.get("short_label"))
    display_color = normalize_cell(row.get("display_color"))
    is_active = parse_bool(row.get("is_active"))
    display_order = parse_int(row.get("display_order"))

    if not program_name:
        errors.append({
            "field": "program_name",
            "error_code": "REQUIRED",
            "message": "program_name は必須です。",
        })

    if is_active is None:
        errors.append({
            "field": "is_active",
            "error_code": "INVALID_BOOLEAN",
            "message": "is_active は true / false で指定してください。",
        })

    if display_order is None:
        errors.append({
            "field": "display_order",
            "error_code": "INVALID_INTEGER",
            "message": "display_order は整数で指定してください。",
        })

    data = {
        "program_name": program_name,
        "short_label": short_label,
        "display_color": display_color,
        "is_active": is_active,
        "display_order": display_order,
    }

    return make_row_result(row_number, data, errors)


def validate_program_schedule_row(row_number: int, row: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []

    program_name = normalize_cell(row.get("program_name"))
    studio_name = normalize_cell(row.get("studio_name"))
    event_date_text = normalize_cell(row.get("event_date"))

    event_date = parse_date(event_date_text)

    if not program_name:
        errors.append({
            "field": "program_name",
            "error_code": "REQUIRED",
            "message": "program_name は必須です。",
        })

    if not studio_name:
        errors.append({
            "field": "studio_name",
            "error_code": "REQUIRED",
            "message": "studio_name は必須です。",
        })

    if not event_date_text:
        errors.append({
            "field": "event_date",
            "error_code": "REQUIRED",
            "message": "event_date は必須です。",
        })
    elif event_date is None:
        errors.append({
            "field": "event_date",
            "error_code": "INVALID_DATE",
            "message": "event_date は yyyy-mm-dd 形式で指定してください。",
        })

    data = {
        "program_name": program_name,
        "studio_name": studio_name,
        "event_date": event_date_text,
    }

    return make_row_result(row_number, data, errors)


def validate_event_row(
    row_number: int,
    row: Dict[str, Any],
    existing_member_names: Set[str],
    existing_event_type_names: Set[str],
) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []

    member_name = normalize_cell(row.get("member_name"))
    event_date_text = normalize_cell(row.get("event_date"))
    event_type_name = normalize_cell(row.get("event_type_name"))
    title = normalize_cell(row.get("title"))
    display_label = normalize_cell(row.get("display_label"))
    memo = normalize_cell(row.get("memo"))

    event_date = parse_date(event_date_text)

    if not member_name:
        errors.append({
            "field": "member_name",
            "error_code": "REQUIRED",
            "message": "member_name は必須です。",
        })
    # Note: Member will be auto-created if not found during import

    if not event_date_text:
        errors.append({
            "field": "event_date",
            "error_code": "REQUIRED",
            "message": "event_date は必須です。",
        })
    elif event_date is None:
        errors.append({
            "field": "event_date",
            "error_code": "INVALID_DATE",
            "message": "event_date は yyyy-mm-dd 形式で指定してください。",
        })

    if not title:
        errors.append({
            "field": "title",
            "error_code": "REQUIRED",
            "message": "title は必須です。",
        })

    # event_type_name is optional - if not found, it will be treated as free text

    if not display_label:
        display_label = title

    data = {
        "member_name": member_name,
        "event_date": event_date_text,
        "event_type_name": event_type_name,
        "title": title,
        "display_label": display_label,
        "memo": memo,
        "source_type": "csv",
        "source_text": f"CSV row {row_number}",
    }

    return make_row_result(row_number, data, errors)


def build_preview(
    import_type: str,
    rows: List[Dict[str, Any]],
    db: Session,
) -> Dict[str, Any]:
    """
    CSV行データをプレビュー形式へ変換する。
    DB更新はしない。
    """
    header_errors = validate_headers(import_type, rows)

    if header_errors:
        return {
            "import_type": import_type,
            "total_rows": len(rows),
            "valid_rows": 0,
            "invalid_rows": len(rows),
            "rows": [{
                "row_number": 1,
                "status": "invalid",
                "data": {},
                "errors": header_errors,
            }],
        }

    existing_member_names = {
        m.display_name
        for m in db.query(CalendarMember).filter(CalendarMember.is_active == True).all()
    }

    existing_event_type_names = {
        e.name
        for e in db.query(CalendarEventType).filter(CalendarEventType.is_active == True).all()
    }

    results: List[Dict[str, Any]] = []

    for index, row in enumerate(rows, start=2):
        if import_type == IMPORT_MEMBERS:
            results.append(validate_member_row(index, row))
        elif import_type == IMPORT_EVENT_TYPES:
            results.append(validate_event_type_row(index, row))
        elif import_type == IMPORT_EVENTS:
            results.append(
                validate_event_row(
                    index,
                    row,
                    existing_member_names,
                    existing_event_type_names,
                )
            )
        elif import_type == IMPORT_PROGRAMS:
            results.append(validate_program_row(index, row))
        elif import_type == IMPORT_PROGRAM_SCHEDULES:
            results.append(validate_program_schedule_row(index, row))

    valid_rows = sum(1 for r in results if r["status"] == "valid")
    invalid_rows = sum(1 for r in results if r["status"] == "invalid")

    return {
        "import_type": import_type,
        "total_rows": len(results),
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "rows": results,
    }


# =========================================================
# CSV preview API
# =========================================================

@router.post("/api/calendar/imports/csv/preview")
async def preview_csv_import(
    import_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        file_bytes = await file.read()
        rows = read_csv_rows(file_bytes)
        preview = build_preview(import_type, rows, db)

        add_audit_log(
            db,
            "csv_preview",
            "csv_import",
            None,
            request={
                "import_type": import_type,
                "filename": file.filename,
                "total_rows": preview["total_rows"],
                "valid_rows": preview["valid_rows"],
                "invalid_rows": preview["invalid_rows"],
            },
        )
        db.commit()

        logger.info(
            "CSV preview completed import_type=%s total=%s valid=%s invalid=%s",
            import_type,
            preview["total_rows"],
            preview["valid_rows"],
            preview["invalid_rows"],
        )

        return success(preview, "CSVプレビューを作成しました")

    except Exception as exc:
        logger.exception("CSV preview failed")
        return error(
            "CSV_PREVIEW_FAILED",
            "CSVプレビューに失敗しました",
            [{"message": str(exc)}],
            "CSV形式・文字コード・ヘッダーを確認してください",
        )


# =========================================================
# CSV execute API
# =========================================================

@router.post("/api/calendar/imports/csv/execute")
def execute_csv_import(
    payload: CsvExecutePayload,
    db: Session = Depends(get_db),
):
    """
    プレビュー済みのJSON行を取り込む。

    members:
      display_name が既存なら更新、なければ作成。

    event_types:
      code が既存なら更新、なければ作成。

    events:
      正式予定には直接登録せず、calendar_event_drafts に登録。

    mode:
      append: 既存データを残して追加・更新
      replace: 既存データを全削除してからインポート
    """
    if payload.import_type not in SUPPORTED_IMPORT_TYPES:
        return error("UNSUPPORTED_IMPORT_TYPE", "未対応のimport_typeです")

    if payload.mode not in ["append", "replace"]:
        return error("INVALID_MODE", "modeは'append'または'replace'を指定してください")

    # Replace mode: delete existing data first
    if payload.mode == "replace":
        if payload.import_type == IMPORT_MEMBERS:
            db.query(CalendarMember).delete()
        elif payload.import_type == IMPORT_EVENT_TYPES:
            db.query(CalendarEventType).delete()
        elif payload.import_type == IMPORT_EVENTS:
            db.query(CalendarEvent).delete()
        elif payload.import_type == IMPORT_PROGRAMS:
            db.query(Program).delete()
        elif payload.import_type == IMPORT_PROGRAM_SCHEDULES:
            db.query(ProgramSchedule).delete()
        db.flush()
        logger.info(f"Replace mode: deleted existing data for {payload.import_type}")

    success_count = 0
    failed_count = 0
    errors: List[Dict[str, Any]] = []
    created_ids: List[int] = []

    try:
        for index, row in enumerate(payload.rows, start=1):
            try:
                if payload.import_type == IMPORT_MEMBERS:
                    item_id = upsert_member_from_csv(db, row)
                    created_ids.append(item_id)

                elif payload.import_type == IMPORT_EVENT_TYPES:
                    item_id = upsert_event_type_from_csv(db, row)
                    created_ids.append(item_id)

                elif payload.import_type == IMPORT_EVENTS:
                    event_id = create_event_from_csv(db, row)
                    created_ids.append(event_id)

                elif payload.import_type == IMPORT_PROGRAMS:
                    program_id = upsert_program_from_csv(db, row)
                    created_ids.append(program_id)

                elif payload.import_type == IMPORT_PROGRAM_SCHEDULES:
                    schedule_id = create_program_schedule_from_csv(db, row)
                    created_ids.append(schedule_id)

                success_count += 1

            except Exception as row_exc:
                failed_count += 1
                errors.append({
                    "row_index": index,
                    "message": str(row_exc),
                    "data": row,
                })

        add_audit_log(
            db,
            "csv_execute",
            "csv_import",
            None,
            request={
                "import_type": payload.import_type,
                "success_count": success_count,
                "failed_count": failed_count,
            },
            response={
                "created_ids": created_ids,
                "errors": errors[:20],
            },
        )

        db.commit()

        logger.info(
            "CSV execute completed import_type=%s success=%s failed=%s",
            payload.import_type,
            success_count,
            failed_count,
        )

        return success(
            {
                "import_type": payload.import_type,
                "success_count": success_count,
                "failed_count": failed_count,
                "created_ids": created_ids,
                "errors": errors,
            },
            f"CSVインポートが完了しました（成功: {success_count}件、失敗: {failed_count}件）",
        )

    except Exception as exc:
        db.rollback()
        logger.exception("CSV execute failed")
        return error(
            "CSV_EXECUTE_FAILED",
            "CSVインポート実行に失敗しました",
            [{"message": str(exc)}],
            "入力JSONと既存マスタを確認してください",
        )


def upsert_member_from_csv(db: Session, row: Dict[str, Any]) -> int:
    display_name = normalize_cell(row.get("display_name"))

    if not display_name:
        raise ValueError("display_name が空です")

    member = (
        db.query(CalendarMember)
        .filter(CalendarMember.display_name == display_name)
        .first()
    )

    values = {
        "display_name": display_name,
        "short_name": normalize_cell(row.get("short_name")),
        "is_active": bool(row.get("is_active")),
        "display_order": int(row.get("display_order") or 0),
    }

    if member:
        for key, value in model_kwargs(CalendarMember, values).items():
            setattr(member, key, value)
        
        # Handle departments
        departments_str = normalize_cell(row.get("departments", ""))
        if departments_str:
            dept_names = [d.strip() for d in departments_str.split(",") if d.strip()]
            
            # Clear existing departments
            db.query(CalendarMemberDepartment).filter(
                CalendarMemberDepartment.member_id == member.id
            ).delete()
            
            # Add new departments
            for dept_name in dept_names:
                dept = db.query(CalendarDepartment).filter(
                    CalendarDepartment.name == dept_name
                ).first()
                if dept:
                    member_dept = CalendarMemberDepartment(
                        member_id=member.id,
                        department_id=dept.id
                    )
                    db.add(member_dept)
        
        db.flush()
        add_audit_log(db, "csv_update_member", "calendar_member", member.id, request=values)
        return member.id

    member = CalendarMember(**model_kwargs(CalendarMember, values))
    db.add(member)
    db.flush()
    
    # Handle departments for new member
    departments_str = normalize_cell(row.get("departments", ""))
    if departments_str:
        dept_names = [d.strip() for d in departments_str.split(",") if d.strip()]
        
        for dept_name in dept_names:
            dept = db.query(CalendarDepartment).filter(
                CalendarDepartment.name == dept_name
            ).first()
            if dept:
                member_dept = CalendarMemberDepartment(
                    member_id=member.id,
                    department_id=dept.id
                )
                db.add(member_dept)
    
    add_audit_log(db, "csv_create_member", "calendar_member", member.id, request=values)
    return member.id


def upsert_event_type_from_csv(db: Session, row: Dict[str, Any]) -> int:
    code = normalize_cell(row.get("code"))

    if not code:
        raise ValueError("code が空です")

    event_type = (
        db.query(CalendarEventType)
        .filter(CalendarEventType.code == code)
        .first()
    )

    values = {
        "code": code,
        "name": normalize_cell(row.get("name")),
        "short_label": normalize_cell(row.get("short_label")),
        "display_color": normalize_cell(row.get("display_color")),
        "display_symbol": normalize_cell(row.get("display_symbol")),
        "is_leave": bool(row.get("is_leave")),
        "is_work_assignment": bool(row.get("is_work_assignment")),
        "requires_capacity_check": bool(row.get("requires_capacity_check")),
        "is_active": bool(row.get("is_active")),
        "display_order": int(row.get("display_order") or 0),
    }

    if event_type:
        for key, value in model_kwargs(CalendarEventType, values).items():
            setattr(event_type, key, value)
        db.flush()
        add_audit_log(db, "csv_update_event_type", "calendar_event_type", event_type.id, request=values)
        return event_type.id

    event_type = CalendarEventType(**model_kwargs(CalendarEventType, values))
    db.add(event_type)
    db.flush()
    add_audit_log(db, "csv_create_event_type", "calendar_event_type", event_type.id, request=values)
    return event_type.id


def upsert_program_from_csv(db: Session, row: Dict[str, Any]) -> int:
    program_name = normalize_cell(row.get("program_name"))

    if not program_name:
        raise ValueError("program_name が空です")

    program = (
        db.query(Program)
        .filter(Program.name == program_name)
        .first()
    )

    values = {
        "name": program_name,
        "short_label": normalize_cell(row.get("short_label")),
        "display_color": normalize_cell(row.get("display_color")),
        "is_active": bool(row.get("is_active")),
        "display_order": int(row.get("display_order") or 0),
    }

    if program:
        for key, value in model_kwargs(Program, values).items():
            setattr(program, key, value)
        db.flush()
        add_audit_log(db, "csv_update_program", "program", program.id, request=values)
        return program.id

    program = Program(**model_kwargs(Program, values))
    db.add(program)
    db.flush()
    add_audit_log(db, "csv_create_program", "program", program.id, request=values)
    return program.id


def create_event_from_csv(db: Session, row: Dict[str, Any]) -> int:
    member_name = normalize_cell(row.get("member_name"))
    event_type_name = normalize_cell(row.get("event_type_name"))
    department_name = normalize_cell(row.get("department_name"))
    event_date = parse_date(row.get("event_date"))
    title = normalize_cell(row.get("title"))

    if event_date is None:
        raise ValueError("event_date が不正です")

    if not title:
        raise ValueError("title が空です")

    # Auto-create member if not found
    member = (
        db.query(CalendarMember)
        .filter(CalendarMember.display_name == member_name)
        .first()
    )
    if not member:
        member = CalendarMember(
            display_name=member_name,
            short_name=member_name[:10] if len(member_name) > 10 else member_name,
            is_active=True,
            display_order=100,
        )
        db.add(member)
        db.flush()
        add_audit_log(db, "csv_auto_create_member", "calendar_member", member.id)

    # Event type is optional - if not found, treat as free text
    event_type = None
    if event_type_name:
        event_type = (
            db.query(CalendarEventType)
            .filter(CalendarEventType.name == event_type_name)
            .first()
        )

    department = None
    if department_name:
        department = (
            db.query(Department)
            .filter(Department.name == department_name)
            .first()
        )

    # Create event directly in calendar_events table
    event = CalendarEvent(
        member_id=member.id if member else None,
        event_date=event_date,
        event_type_id=event_type.id if event_type else None,
        department_id=department.id if department else None,
        title=title,
        display_label=normalize_cell(row.get("display_label")) or title,
        memo=normalize_cell(row.get("memo")),
        source_type="csv",
        approval_status="approved",
    )
    db.add(event)
    db.flush()
    add_audit_log(db, "csv_import_event", "calendar_event", event.id)
    
    return event.id


def create_program_schedule_from_csv(db: Session, row: Dict[str, Any]) -> int:
    program_name = normalize_cell(row.get("program_name"))
    studio_name = normalize_cell(row.get("studio_name"))
    event_date = parse_date(row.get("event_date"))

    if event_date is None:
        raise ValueError("event_date が不正です")

    # Find program by name
    program = (
        db.query(Program)
        .filter(Program.name == program_name)
        .first()
    )
    if not program:
        raise ValueError(f"プログラムが見つかりません: {program_name}")

    # Find studio by name
    studio = (
        db.query(Studio)
        .filter(Studio.name == studio_name)
        .first()
    )
    if not studio:
        raise ValueError(f"スタジオが見つかりません: {studio_name}")

    # Create program schedule
    schedule = ProgramSchedule(
        program_id=program.id,
        studio_id=studio.id,
        event_date=event_date,
    )
    db.add(schedule)
    db.flush()
    add_audit_log(db, "csv_import_program_schedule", "program_schedule", schedule.id)
    
    return schedule.id


# =========================================================
# CSV export API
# =========================================================

@router.get("/api/calendar/exports/csv")
def export_csv(
    export_type: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    template: bool = False,
    db: Session = Depends(get_db),
):
    if export_type not in SUPPORTED_EXPORT_TYPES:
        return error("UNSUPPORTED_EXPORT_TYPE", "未対応のexport_typeです")

    try:
        if export_type == IMPORT_MEMBERS:
            if template:
                records = [{"display_name": "サンプル氏名", "short_name": "サンプル", "departments": "部署A, 部署B", "is_active": True, "display_order": 100}]
            else:
                records = export_members(db)
            filename = "calendar_members.csv"

        elif export_type == IMPORT_EVENT_TYPES:
            if template:
                records = [{"code": "rd", "name": "RD", "short_label": "RD", "display_color": "#dbeafe", "display_symbol": "", "is_leave": False, "is_work_assignment": True, "requires_capacity_check": True, "is_active": True, "display_order": 100}]
            else:
                records = export_event_types(db)
            filename = "calendar_event_types.csv"

        elif export_type == IMPORT_EVENTS:
            if template:
                records = [{"member_name": "サンプル氏名", "event_date": "2026-06-01", "event_type_name": "RD", "department_name": "部署A", "title": "RD", "display_label": "", "memo": ""}]
            else:
                records = export_events(db)
            filename = "calendar_events.csv"

        elif export_type == IMPORT_PROGRAMS:
            if template:
                records = [{"program_name": "サンプル番組", "short_label": "サンプル", "display_color": "#dbeafe", "is_active": True, "display_order": 100}]
            else:
                records = export_programs(db)
            filename = "programs.csv"

        elif export_type == IMPORT_PROGRAM_SCHEDULES:
            if template:
                records = [{"program_name": "サンプル番組", "studio_name": "スタジオA", "event_date": "2026-06-01"}]
            else:
                records = export_program_schedules(db)
            filename = "program_schedules.csv"

        elif export_type == "monthly":
            if year is None or month is None:
                return error("YEAR_MONTH_REQUIRED", "monthly export では year と month が必要です")
            records = export_monthly_events(db, year, month)
            filename = f"calendar_monthly_{year}_{month:02d}.csv"

        else:
            return error("UNSUPPORTED_EXPORT_TYPE", "未対応のexport_typeです")

        csv_text = build_csv_text(export_type, records)

        add_audit_log(
            db,
            "csv_export",
            "csv_export",
            None,
            request={
                "export_type": export_type,
                "year": year,
                "month": month,
                "record_count": len(records),
            },
        )
        db.commit()

        logger.info(
            "CSV export completed export_type=%s count=%s",
            export_type,
            len(records),
        )

        return Response(
            content=csv_text.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    except Exception as exc:
        logger.exception("CSV export failed")
        return error(
            "CSV_EXPORT_FAILED",
            "CSVエクスポートに失敗しました",
            [{"message": str(exc)}],
            "export_type、year、monthを確認してください",
        )


def export_members(db: Session) -> List[Dict[str, Any]]:
    members = db.query(CalendarMember).order_by(CalendarMember.display_order, CalendarMember.id).all()

    result = []
    for m in members:
        # Get department names
        dept_names = []
        for md in m.departments:
            if md.department:
                dept_names.append(md.department.name)
        
        result.append({
            "display_name": m.display_name,
            "short_name": m.short_name,
            "departments": ", ".join(dept_names),
            "is_active": m.is_active,
            "display_order": m.display_order,
        })
    
    return result


def export_event_types(db: Session) -> List[Dict[str, Any]]:
    event_types = db.query(CalendarEventType).order_by(CalendarEventType.display_order, CalendarEventType.id).all()

    return [
        {
            "code": e.code,
            "name": e.name,
            "short_label": e.short_label,
            "display_color": e.display_color,
            "display_symbol": e.display_symbol,
            "is_leave": e.is_leave,
            "is_work_assignment": e.is_work_assignment,
            "requires_capacity_check": e.requires_capacity_check,
            "is_active": e.is_active,
            "display_order": e.display_order,
        }
        for e in event_types
    ]


def export_programs(db: Session) -> List[Dict[str, Any]]:
    programs = db.query(Program).order_by(Program.display_order, Program.id).all()

    return [
        {
            "program_name": p.name,
            "short_label": p.short_label,
            "display_color": p.display_color,
            "is_active": p.is_active,
            "display_order": p.display_order,
        }
        for p in programs
    ]


def export_program_schedules(db: Session) -> List[Dict[str, Any]]:
    schedules = (
        db.query(ProgramSchedule)
        .join(Program, ProgramSchedule.program_id == Program.id)
        .join(Studio, ProgramSchedule.studio_id == Studio.id)
        .order_by(ProgramSchedule.event_date, ProgramSchedule.id)
        .all()
    )

    return [
        {
            "program_name": s.program.name,
            "studio_name": s.studio.studio_name,
            "event_date": s.event_date.isoformat(),
        }
        for s in schedules
    ]


def export_events(db: Session) -> List[Dict[str, Any]]:
    events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.is_archived == False)
        .order_by(CalendarEvent.event_date, CalendarEvent.id)
        .all()
    )

    return [
        {
            "member_name": e.member.display_name if e.member else "",
            "event_date": e.event_date.isoformat() if e.event_date else "",
            "event_type_name": e.event_type.name if e.event_type else "",
            "department_name": e.department.name if e.department else "",
            "title": e.title,
            "display_label": e.display_label,
            "memo": getattr(e, "memo", "") or "",
        }
        for e in events
    ]


def export_monthly_events(db: Session, year: int, month: int) -> List[Dict[str, Any]]:
    events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.is_archived == False)
        .filter(extract("year", CalendarEvent.event_date) == year)
        .filter(extract("month", CalendarEvent.event_date) == month)
        .order_by(CalendarEvent.event_date, CalendarEvent.id)
        .all()
    )

    return [
        {
            "member_name": e.member.display_name if e.member else "",
            "event_date": e.event_date.isoformat() if e.event_date else "",
            "event_type_name": e.event_type.name if e.event_type else "",
            "department_name": e.department.name if e.department else "",
            "title": e.title,
            "display_label": e.display_label,
            "memo": getattr(e, "memo", "") or "",
        }
        for e in events
    ]


def build_csv_text(export_type: str, records: List[Dict[str, Any]]) -> str:
    """
    JSON配列をUTF-8 BOM付きCSV文字列に変換する。
    Excelで開きやすいようにBOMを付ける。
    """
    if export_type == IMPORT_MEMBERS:
        headers = [
            "display_name",
            "short_name",
            "departments",
            "is_active",
            "display_order",
        ]

    elif export_type == IMPORT_EVENT_TYPES:
        headers = [
            "code",
            "name",
            "short_label",
            "display_color",
            "display_symbol",
            "is_leave",
            "is_work_assignment",
            "requires_capacity_check",
            "is_active",
            "display_order",
        ]

    elif export_type == IMPORT_PROGRAMS:
        headers = [
            "program_name",
            "short_label",
            "display_color",
            "is_active",
            "display_order",
        ]

    elif export_type == IMPORT_PROGRAM_SCHEDULES:
        headers = [
            "program_name",
            "studio_name",
            "event_date",
        ]

    elif export_type in {IMPORT_EVENTS, "monthly"}:
        headers = [
            "member_name",
            "event_date",
            "event_type_name",
            "department_name",
            "title",
            "display_label",
            "memo",
        ]

    else:
        raise ValueError(f"未対応のexport_typeです: {export_type}")

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()

    for record in records:
        writer.writerow({
            header: format_csv_value(record.get(header))
            for header in headers
        })

    return "\ufeff" + stream.getvalue()


def format_csv_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)