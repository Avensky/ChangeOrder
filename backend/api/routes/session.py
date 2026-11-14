"""GET /api/v1/me: who the signed-in caller is, so the app can show their screens."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.auth import Caller, current_caller

# Mounted by changes.py, whose /api/v1 prefix applies to these paths.
router = APIRouter(tags=["session"])


class MeOut(BaseModel):
    id: int
    name: str
    role: str


@router.get("/me", response_model=MeOut)
def me(caller: Caller = Depends(current_caller)):
    return MeOut(id=caller.id, name=caller.name, role=caller.role)
