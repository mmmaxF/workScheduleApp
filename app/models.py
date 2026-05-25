from datetime import datetime, date
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class CalendarMember(Base):
    __tablename__ = "calendar_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    short_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class CalendarEventType(Base):
    __tablename__ = "calendar_event_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    short_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    display_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    display_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_leave: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_work_assignment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_capacity_check: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class CalendarEventDraft(Base):
    __tablename__ = "calendar_event_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_name_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    member_id: Mapped[int | None] = mapped_column(ForeignKey("calendar_members.id"), nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_type_name_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_type_id: Mapped[int | None] = mapped_column(ForeignKey("calendar_event_types.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    display_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="not_validated", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    member = relationship("CalendarMember")
    event_type = relationship("CalendarEventType")

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("calendar_members.id"), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_type_id: Mapped[int] = mapped_column(ForeignKey("calendar_event_types.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    display_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(30), default="approved", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    member = relationship("CalendarMember")
    event_type = relationship("CalendarEventType")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(50), default="system", nullable=False)
    actor_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
