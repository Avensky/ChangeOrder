"""Database records for changes, proposals, GC approval and alerts (schema v2).

These models describe the schema. Existing Supabase tables are changed only by
the SQL files in backend/db/migrations/; SQLModel.metadata.create_all() does
not alter old tables. Keep the two in step: a change here needs a migration.

Rules the schema enforces (see AGENTS.md, "Domain rules"):

- Tenants: every table except Company carries company_id. A reference to
  another tenant row is a two-column key (company_id, <column>), so a row can
  only point at rows of its own company.
- Personas: field, estimator, manager, gc. A GC never has a sign-in account.
- One status set, stored on the change (ChangeEvent.status).
- Fast track: only a high-priority change can be authorized to proceed.
- Money is integer cents plus a currency code.
- GC links store the SHA-256 hash of the token, never the token. A
  notification never holds a link that carries a token.
- The field report (ChangeEvent.description) is never overwritten by the
  reviewed proposal (ChangeOrderRevision.scope).
- A project's work order is not a table. It is the project's approved
  changes, each with the revision the GC approved; see migrations/README.md.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    text,
)
from sqlmodel import Field, SQLModel

ROLES = ("field", "estimator", "manager", "gc")
PRIORITIES = ("normal", "high")
# The single status set for a change. authorized_to_proceed is fast track only.
CHANGE_STATUSES = (
    "submitted",
    "in_review",
    "authorized_to_proceed",
    "awaiting_gc",
    "approved",
    "declined",
    "withdrawn",
)
# State of one request sent to the GC. This is not the status of the change.
APPROVAL_REQUEST_STATUSES = ("pending", "approved", "declined", "expired", "canceled")
DECISIONS = ("approved", "declined")
# One alert type for each status a change can move to.
NOTIFICATION_TYPES = (
    "change_submitted",
    "change_in_review",
    "work_authorized",
    "approval_requested",
    "change_approved",
    "change_declined",
    "change_withdrawn",
)
NOTIFICATION_STATUSES = ("pending", "sent")
DEFAULT_CURRENCY = "USD"
_CURRENCY_RULE = "length(currency) = 3 AND currency = upper(currency)"


def utc_now() -> datetime:
    return datetime.now(UTC)


def _one_of(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _utc_column(*, nullable: bool = False) -> Column:
    return Column(DateTime(timezone=True), nullable=nullable)


def _company_key(table: str) -> UniqueConstraint:
    """Lets other tables reference this one by (company_id, id)."""
    return UniqueConstraint("company_id", "id", name=f"uq_{table}_company_id_id")


def _same_company(table: str, column: str, target: str) -> ForeignKeyConstraint:
    """Foreign key that also requires the referenced row to be in the same company."""
    return ForeignKeyConstraint(
        ["company_id", column],
        [f"{target}.company_id", f"{target}.id"],
        name=f"fk_{table}_{column}_company",
    )


class Company(SQLModel, table=True):
    """The tenant. Every other record belongs to exactly one company."""

    __tablename__ = "company"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class User(SQLModel, table=True):
    """A person in one company. Staff sign in through Supabase; a GC never does."""

    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint(_one_of("role", ROLES), name="user_role_valid"),
        CheckConstraint("role <> 'gc' OR auth_user_id IS NULL", name="user_gc_has_no_account"),
        _company_key("user"),
        UniqueConstraint("company_id", "email", name="uq_user_company_id_email"),
        Index("ix_user_company_id_role", "company_id", "role"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    role: str
    name: str = Field(index=True)
    phone: str | None = Field(default=None, index=True)
    # Where the GC link is sent, and the address staff sign in with.
    email: str | None = None
    # The Supabase account id (the "sub" of a verified token). Empty for a GC.
    auth_user_id: uuid.UUID | None = Field(default=None, unique=True, index=True)


class Project(SQLModel, table=True):
    """A job. Its work order is its base budget plus its approved changes."""

    __tablename__ = "project"
    __table_args__ = (
        CheckConstraint(_CURRENCY_RULE, name="project_currency_valid"),
        _company_key("project"),
        UniqueConstraint("company_id", "slug", name="uq_project_company_id_slug"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    # Short name used in URLs and by the app, for example "north-park".
    slug: str
    name: str
    # The contract amount before any change order. Empty until it is known.
    base_budget_cents: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    currency: str = Field(default=DEFAULT_CURRENCY)
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class ChangeEvent(SQLModel, table=True):
    """The change reported from the field. Its status is the status of the change."""

    __tablename__ = "change_event"
    __table_args__ = (
        CheckConstraint(_one_of("severity", PRIORITIES), name="change_event_severity_valid"),
        CheckConstraint(_one_of("status", CHANGE_STATUSES), name="change_event_status_valid"),
        CheckConstraint(
            "(authorized_by_id IS NULL) = (authorized_at IS NULL)",
            name="change_event_authorization_complete",
        ),
        CheckConstraint(
            "authorized_at IS NULL OR severity = 'high'",
            name="change_event_authorization_high_priority_only",
        ),
        CheckConstraint(
            "status <> 'authorized_to_proceed' OR authorized_at IS NOT NULL",
            name="change_event_authorized_status_needs_authorization",
        ),
        _company_key("change_event"),
        UniqueConstraint("company_id", "number", name="uq_change_event_company_id_number"),
        _same_company("change_event", "project_id", "project"),
        _same_company("change_event", "submitted_by_id", "user"),
        _same_company("change_event", "authorized_by_id", "user"),
        Index("ix_change_event_company_id_status", "company_id", "status"),
        Index("ix_change_event_company_id_project_id", "company_id", "project_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    project_id: int
    # Human-readable number, unique in the company. Shown as "CO-<number>".
    number: int
    submitted_by_id: int = Field(index=True)
    title: str
    # The original field report. Reviewed wording goes on the revision.
    description: str
    # The priority flag. The API and the app call this field "severity".
    severity: str = Field(default="normal")
    status: str = Field(default="submitted")
    # Fast track: the manager who let work start before the estimate, and when.
    authorized_by_id: int | None = None
    authorized_at: datetime | None = Field(default=None, sa_column=_utc_column(nullable=True))
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class Photo(SQLModel, table=True):
    """One photo of a change. Context for people, not AI input."""

    __tablename__ = "photo"
    __table_args__ = (
        _same_company("photo", "change_event_id", "change_event"),
        Index("ix_photo_company_id_change_event_id", "company_id", "change_event_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    change_event_id: int
    # Key of the stored object in the bucket. Not a public URL.
    storage_key: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class ChangeHistory(SQLModel, table=True):
    """One entry in a change's timeline: the status it moved to, who, and when.

    Entries are only ever added. Write one in the same transaction as the
    status change it records.
    """

    __tablename__ = "change_history"
    __table_args__ = (
        CheckConstraint(_one_of("status", CHANGE_STATUSES), name="change_history_status_valid"),
        _same_company("change_history", "change_event_id", "change_event"),
        _same_company("change_history", "actor_user_id", "user"),
        Index("ix_change_history_company_id_change_event_id", "company_id", "change_event_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    change_event_id: int
    # The status the change moved to.
    status: str
    # The line shown in the timeline, for example "Sent to the GC".
    title: str
    # Who did it. Empty when the system did. The name is copied so the
    # timeline still reads correctly after a user is renamed.
    actor_user_id: int | None = None
    actor_name: str
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class AiSuggestion(SQLModel, table=True):
    """An AI suggestion for the estimator. Advisory only; it decides nothing."""

    __tablename__ = "ai_suggestion"
    __table_args__ = (
        CheckConstraint(_CURRENCY_RULE, name="ai_suggestion_currency_valid"),
        CheckConstraint("suggested_cost_cents >= 0", name="ai_suggestion_cost_valid"),
        CheckConstraint("suggested_timeline_days >= 0", name="ai_suggestion_timeline_valid"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ai_suggestion_confidence_valid",
        ),
        _same_company("ai_suggestion", "change_event_id", "change_event"),
        Index("ix_ai_suggestion_company_id_change_event_id", "company_id", "change_event_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    change_event_id: int
    # The originally contracted scope the estimator gave the model to compare against.
    original_scope: str
    suggested_scope: str
    suggested_cost_cents: int = Field(sa_column=Column(BigInteger, nullable=False))
    currency: str = Field(default=DEFAULT_CURRENCY)
    suggested_timeline_days: int
    # The model's reasons, assumptions and limits.
    rationale: str
    # True when the model thinks the work is already in the original scope.
    in_scope: bool
    model_id: str | None = None
    confidence: float | None = None
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class ChangeOrder(SQLModel, table=True):
    """The estimator's proposal for one change. Its terms live in the revisions."""

    __tablename__ = "change_order"
    __table_args__ = (
        _company_key("change_order"),
        _same_company("change_order", "change_event_id", "change_event"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    change_event_id: int = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class ChangeOrderRevision(SQLModel, table=True):
    """Terms proposed to the GC. A sent (frozen) revision is never edited in place."""

    __tablename__ = "change_order_revision"
    __table_args__ = (
        UniqueConstraint("change_order_id", "revision_number", name="uq_order_revision_number"),
        CheckConstraint(_CURRENCY_RULE, name="change_order_revision_currency_valid"),
        CheckConstraint(
            "requested_timeline_days >= 0",
            name="change_order_revision_timeline_valid",
        ),
        CheckConstraint(
            "frozen_at IS NULL OR "
            "(proposed_cost_cents IS NOT NULL AND requested_timeline_days IS NOT NULL)",
            name="change_order_revision_sent_has_terms",
        ),
        _company_key("change_order_revision"),
        _same_company("change_order_revision", "change_order_id", "change_order"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    change_order_id: int = Field(index=True)
    revision_number: int
    # Optional. When empty, the change's own title is used.
    title: str | None = None
    reason: str | None = None
    # The reviewed wording of the work, as proposed to the GC.
    scope: str
    # Money is integer cents plus a currency code, never a float.
    proposed_cost_cents: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    currency: str = Field(default=DEFAULT_CURRENCY)
    # Extra calendar days requested for the work; 0 means no schedule change.
    requested_timeline_days: int | None = None
    frozen_at: datetime | None = Field(default=None, sa_column=_utc_column(nullable=True))
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class ApprovalRequest(SQLModel, table=True):
    """A request to one GC to decide on one frozen revision."""

    __tablename__ = "approval_request"
    __table_args__ = (
        CheckConstraint(
            _one_of("status", APPROVAL_REQUEST_STATUSES),
            name="approval_request_status_valid",
        ),
        _company_key("approval_request"),
        _same_company("approval_request", "revision_id", "change_order_revision"),
        _same_company("approval_request", "gc_user_id", "user"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    revision_id: int = Field(index=True)
    gc_user_id: int = Field(index=True)
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class ApprovalLink(SQLModel, table=True):
    """The emailed GC link for one approval request.

    Only the SHA-256 hash of the token is stored; the token itself is shown
    once, in the email. A link is usable while it is neither expired nor
    revoked. Opening it never decides anything.
    """

    __tablename__ = "approval_link"
    __table_args__ = (
        # A SHA-256 hex digest is 64 characters; the raw token is shorter.
        CheckConstraint("length(token_hash) = 64", name="approval_link_token_hash_is_sha256"),
        _same_company("approval_link", "approval_request_id", "approval_request"),
        Index(
            "ix_approval_link_company_id_approval_request_id",
            "company_id",
            "approval_request_id",
        ),
        # At most one link per request that has not been revoked.
        Index(
            "uq_approval_link_live_request",
            "approval_request_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
            sqlite_where=text("revoked_at IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    approval_request_id: int
    token_hash: str = Field(unique=True, index=True)
    expires_at: datetime = Field(sa_column=_utc_column())
    revoked_at: datetime | None = Field(default=None, sa_column=_utc_column(nullable=True))
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class ApprovalDecision(SQLModel, table=True):
    """The GC's one final decision for one approval request."""

    __tablename__ = "approval_decision"
    __table_args__ = (
        CheckConstraint(_one_of("decision", DECISIONS), name="approval_decision_valid"),
        _same_company("approval_decision", "request_id", "approval_request"),
        _same_company("approval_decision", "revision_id", "change_order_revision"),
        _same_company("approval_decision", "decided_by_id", "user"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    request_id: int = Field(unique=True, index=True)
    revision_id: int
    decided_by_id: int = Field(index=True)
    decision: str
    decided_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())


class Notification(SQLModel, table=True):
    """An alert for one recipient about one change."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(_one_of("type", NOTIFICATION_TYPES), name="notification_type_valid"),
        CheckConstraint(_one_of("status", NOTIFICATION_STATUSES), name="notification_status_valid"),
        # The GC token exists only in the email. It must never be saved here.
        CheckConstraint(
            "message NOT LIKE '%token=%' AND (link_target IS NULL OR link_target NOT LIKE '%token=%')",
            name="notification_holds_no_token",
        ),
        _same_company("notifications", "report_id", "change_event"),
        _same_company("notifications", "recipient_user_id", "user"),
        Index("ix_notifications_company_id_recipient_user_id", "company_id", "recipient_user_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    # The change this alert is about (change_event.id).
    report_id: int = Field(index=True)
    recipient_user_id: int
    type: str = Field(default="change_submitted")
    # The text shown to the recipient.
    message: str
    # Where the alert opens in the app, for example "/changes/12". Never a token link.
    link_target: str | None = None
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=utc_now, sa_column=_utc_column())
    sent_at: datetime | None = Field(default=None, sa_column=_utc_column(nullable=True))


# Every table whose rows belong to a company. Query these through
# db.database.company_select() so the company filter cannot be forgotten.
TENANT_MODELS: tuple[type[SQLModel], ...] = (
    User,
    Project,
    ChangeEvent,
    Photo,
    ChangeHistory,
    AiSuggestion,
    ChangeOrder,
    ChangeOrderRevision,
    ApprovalRequest,
    ApprovalLink,
    ApprovalDecision,
    Notification,
)
