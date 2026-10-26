from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.database import read_json
from backend.security import User, require_role


router = APIRouter(prefix="/api/psychiatrist", tags=["psychiatrist"])


@router.get("/{psychiatrist_id}/patients")
def assigned_patients(
    psychiatrist_id: int,
    user: User = Depends(require_role("Psychiatrist")),
) -> list[dict[str, Any]]:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only view your own assigned patients")
    return [
        patient
        for patient in read_json("patients.json")
        if patient.get("assigned_psychiatrist_id") == psychiatrist_id
        and patient.get("status") == "Active"
    ]
