from enum import Enum
from pydantic import BaseModel

class Status(str, Enum):
    submitted = "submitted"
    awaiting_client = "awaiting_client"
    approved = "approved"
    rejected = "rejected"

class Severity(str, Enum):
    normal = "normal"
    high = "high"

class ChangeOut(BaseModel):
    id: str
    description: str
    severity: Severity
    status: Status
    photo_key: str | None = None
