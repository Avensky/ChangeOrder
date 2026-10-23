from enum import Enum
from typing import Annotated

from pydantic import BaseModel, StringConstraints

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
    photo_key: str | None = None
