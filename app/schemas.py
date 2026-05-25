from datetime import date
from pydantic import BaseModel, Field

class ApiResponse(BaseModel):
    ok: bool
    data: object | None = None
    message: str | None = None
    error_code: str | None = None
    details: list | None = None
    suggestion: str | None = None

def success(data=None, message="処理が完了しました"):
    return {"ok": True, "data": data if data is not None else {}, "message": message}

def error(error_code, message, details=None, suggestion=""):
    return {
        "ok": False,
        "error_code": error_code,
        "message": message,
        "details": details or [],
        "suggestion": suggestion,
    }

class MemberCreate(BaseModel):
    display_name: str = Field(..., min_length=1)
    short_name: str | None = None
    display_order: int = 100

class MemberUpdate(BaseModel):
    display_name: str | None = None
    short_name: str | None = None
    display_order: int | None = None
    is_active: bool | None = None

class EventTypeCreate(BaseModel):
    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    short_label: str | None = None
    display_color: str | None = None
    display_symbol: str | None = None
    is_leave: bool = False
    is_work_assignment: bool = False
    requires_capacity_check: bool = False
    display_order: int = 100

class EventTypeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    short_label: str | None = None
    display_color: str | None = None
    display_symbol: str | None = None
    is_leave: bool | None = None
    is_work_assignment: bool | None = None
    requires_capacity_check: bool | None = None
    display_order: int | None = None
    is_active: bool | None = None

class DraftCreate(BaseModel):
    member_name_raw: str | None = None
    member_id: int | None = None
    event_date: date
    event_type_name_raw: str | None = None
    event_type_id: int | None = None
    title: str
    display_label: str | None = None
    memo: str | None = None
    source_type: str = "manual"
    source_text: str | None = None

class EventCreate(BaseModel):
    member_id: int
    event_date: date
    event_type_id: int
    title: str
    display_label: str | None = None
    memo: str | None = None
    source_type: str = "manual"
