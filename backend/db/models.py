"""Database records for reports, proposals, client decisions, and alerts.

These models describe the intended schema. Existing Supabase tables need an
explicit migration; SQLModel.metadata.create_all() does not alter old tables.
"""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint("role IN ('contractor', 'admin', 'client')", name="user_role_valid"),
    )

    id: int | None = Field(default=None, primary_key=True)
    role: str
    name: str = Field(index=True)
    phone: str | None = Field(default=None, index=True)


class ChangeEvent(SQLModel, table=True):
    """The contractor's original report, separate from an office proposal."""

    __tablename__ = "change_event"
    __table_args__ = (
        CheckConstraint("severity IN ('normal', 'high')", name="change_event_severity_valid"),
        CheckConstraint(
            "status IN ('submitted', 'office_review', 'needs_information', 'resolved')",
            name="change_event_status_valid",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    contractor_id: int = Field(foreign_key="user.id", index=True)
    description: str
    severity: str = Field(default="normal")
    photo_key: str | None = None
    status: str = Field(default="submitted", index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class ChangeOrder(SQLModel, table=True):
    """Office proposal arising from one field report."""

    __tablename__ = "change_order"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'awaiting_client', 'approved', 'declined', 'withdrawn')",
            name="change_order_status_valid",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    change_event_id: int = Field(foreign_key="change_event.id", unique=True, index=True)
    status: str = Field(default="draft", index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class ChangeOrderRevision(SQLModel, table=True):
    """Proposed client terms; a sent revision is never edited in place."""

    __tablename__ = "change_order_revision"
    __table_args__ = (
        UniqueConstraint("change_order_id", "revision_number", name="uq_order_revision_number"),
    )

    id: int | None = Field(default=None, primary_key=True)
    change_order_id: int = Field(foreign_key="change_order.id", index=True)
    revision_number: int
    title: str
    reason: str
    scope: str
    frozen_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class ApprovalRequest(SQLModel, table=True):
    __tablename__ = "approval_request"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'declined', 'expired', 'canceled')",
            name="approval_request_status_valid",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    revision_id: int = Field(foreign_key="change_order_revision.id", index=True)
    client_id: int = Field(foreign_key="user.id", index=True)
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class ApprovalDecision(SQLModel, table=True):
    """One final client decision for one requested revision."""

    __tablename__ = "approval_decision"
    __table_args__ = (
        CheckConstraint("decision IN ('approved', 'declined')", name="approval_decision_valid"),
    )

    id: int | None = Field(default=None, primary_key=True)
    request_id: int = Field(foreign_key="approval_request.id", unique=True, index=True)
    revision_id: int = Field(foreign_key="change_order_revision.id")
    approved_by_id: int = Field(foreign_key="user.id", index=True)
    decision: str
    decided_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('report_submitted', 'approval_requested', 'report_approved', 'report_rejected')",
            name="notification_type_valid",
        ),
        CheckConstraint("status IN ('pending', 'sent')", name="notification_status_valid"),
    )

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="change_event.id", index=True)
    recipient_user_id: int = Field(foreign_key="user.id", index=True)
    type: str = Field(default="report_submitted")
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    sent_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
