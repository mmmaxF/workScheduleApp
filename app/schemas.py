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
    member_id: int | None = None
    member_name: str | None = None
    event_date: date
    event_type_id: int | None = None
    event_type_name: str | None = None
    title: str
    display_label: str | None = None
    memo: str | None = None
    source_type: str = "manual"

class EventBulkCreate(BaseModel):
    events: list[EventCreate]

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    display_order: int = 100

class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    is_active: bool | None = None
    display_order: int | None = None

class MemberDepartmentsUpdate(BaseModel):
    department_ids: list[int]

class CapacityRuleCreate(BaseModel):
    event_type_id: int
    department_id: int | None = None
    day_type: str = Field(..., pattern="^(weekday|weekend|all)$")
    required_count: int = Field(..., ge=0)

class CapacityRuleUpdate(BaseModel):
    event_type_id: int | None = None
    department_id: int | None = None
    day_type: str | None = Field(None, pattern="^(weekday|weekend|all)$")
    required_count: int | None = Field(None, ge=0)
    is_active: bool | None = None

class StudioCreate(BaseModel):
    name: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    display_order: int = 100

class StudioUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    is_active: bool | None = None
    display_order: int | None = None

class ProgramCreate(BaseModel):
    name: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    short_label: str | None = None
    display_color: str | None = None
    display_order: int = 100

class ProgramUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    short_label: str | None = None
    display_color: str | None = None
    is_active: bool | None = None
    display_order: int | None = None

class ProgramScheduleCreate(BaseModel):
    program_id: int | None = None
    program_name: str | None = None
    studio_id: int | None = None
    studio_name: str | None = None
    event_date: date

class ProgramScheduleBulkCreate(BaseModel):
    schedules: list[ProgramScheduleCreate]
