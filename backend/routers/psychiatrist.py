from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.database import get_patients
from backend.security import User, require_role


router = APIRouter(prefix="/api/psychiatrist", tags=["psychiatrist"])


@router.get("/{psychiatrist_id}/patients")
def assigned_patients(
    psychiatrist_id: int,
    user: User = Depends(require_role("Psychiatrist")),
) -> list[dict[str, Any]]:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only view your own assigned patients")
    return get_patients(status="Active", assigned_psychiatrist_id=psychiatrist_id)
