from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# CHANGED: Share one description rule between the multipart request and its
# response. Strip outside spaces; reject blank text or more than 500 characters.
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class Status(str, Enum):
    submitted = "submitted"
    awaiting_client = "awaiting_client"
    approved = "approved"
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
    scope: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
        ]
        | None
    ) = None
    amount: float = Field(ge=0, le=100000000, allow_inf_nan=False, multiple_of=0.01)
    impact_days: int = Field(ge=0, le=3650)


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
