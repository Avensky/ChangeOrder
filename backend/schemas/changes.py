from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# CHANGED: Share one description rule between the multipart request and its
# response. Strip outside spaces; reject blank text or more than 500 characters.
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class Status(str, Enum):
    # The status set from AGENTS.md, matching CHANGE_STATUSES in B2's models.
    submitted = "submitted"
    in_review = "in_review"
    # Fast track only: the manager authorized work before the estimate exists.
    authorized_to_proceed = "authorized_to_proceed"
    awaiting_gc = "awaiting_gc"
    approved = "approved"
    declined = "declined"
    withdrawn = "withdrawn"
    # LEGACY: the names the merged frontend still sends and reads. These keep
    # the demo working until U3 moves it onto the routes below; remove both
    # once nothing calls /admin-approve. awaiting_client == awaiting_gc and
    # rejected == declined.
    awaiting_client = "awaiting_client"
    rejected = "rejected"


class Severity(str, Enum):
    # The frontend calls this "Priority"; keep the existing API name/values
    # so the upload route and the existing review rules continue to agree.
    normal = "normal"
    high = "high"


class ChangeOut(BaseModel):
    id: str
    description: Description
    severity: Severity
    status: Status
    photo_keys: list[str] = Field(default_factory=list)


class HistoryEvent(BaseModel):
    id: str
    changeId: str
    title: str
    person: str
    time: str
    kind: str


class SuggestionRequest(BaseModel):
    original_scope: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=10000)
    ]


class Suggestion(BaseModel):
    scope: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    amount: float = Field(ge=0, le=100000000, allow_inf_nan=False, multiple_of=0.01)
    impact_days: int = Field(ge=0, le=3650)
    rationale: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    in_scope: bool


class ReviewTerms(BaseModel):
    # LEGACY: the float-money body /admin-approve still accepts. Prefer
    # EstimatorReview below, which carries integer cents per AGENTS.md.
    scope: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
        ]
        | None
    ) = None
    amount: float = Field(ge=0, le=100000000, allow_inf_nan=False, multiple_of=0.01)
    impact_days: int = Field(ge=0, le=3650)


# Three uppercase letters, matching B2's change_order_revision_currency_valid.
Currency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class EstimatorReview(BaseModel):
    """What the estimator saves: scope, proposed cost and requested timeline.

    Money is integer cents plus a currency code, never a float. The field
    names match B2's ChangeOrderRevision so the repository swap in J4 is a
    rename and nothing more.
    """

    scope: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
        ]
        | None
    ) = None
    # 10 billion cents is 100 million dollars, the same ceiling as the float field.
    proposed_cost_cents: int = Field(ge=0, le=10_000_000_000)
    requested_timeline_days: int = Field(ge=0, le=3650)
    currency: Currency = "USD"


class WorkspaceChangeOut(ChangeOut):
    code: str
    title: str
    project_id: str
    submitted_by: str
    author: str
    created_at: str
    amount: float
    impact_days: int
    sent_for_approval: bool
    history: list[HistoryEvent]
    suggestion: Suggestion | None = None
    approved_scope: str | None = None
    # The estimator's terms. None until a review is saved, which is why the GC
    # link can show "no estimate yet" for a fast-tracked change.
    proposed_cost_cents: int | None = None
    requested_timeline_days: int | None = None
    currency: Currency = "USD"
    # Set only by the fast-track authorization, and only on high priority.
    authorized_at: str | None = None
    authorized_by: str | None = None
