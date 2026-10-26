from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.database import read_json, transaction, write_json
from backend.schemas import AssignCaseRequest
from backend.security import User, require_role
from backend.telegram_client import send_telegram_message


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/pending-patients")
def pending_patients(_: User = Depends(require_role("Admin"))) -> list[dict[str, Any]]:
    return [
        patient
        for patient in read_json("patients.json")
        if patient.get("status") == "Pending_Assignment"
    ]


@router.get("/psychiatrists")
def psychiatrists(_: User = Depends(require_role("Admin"))) -> list[dict[str, Any]]:
    return read_json("psychiatrists.json")


@router.post("/assign-case")
async def assign_case(
    request: AssignCaseRequest,
    _: User = Depends(require_role("Admin")),
) -> dict[str, Any]:
    with transaction():
        patients = read_json("patients.json")
        psychiatrists = read_json("psychiatrists.json")
        patient = next((item for item in patients if item.get("telegram_id") == request.telegram_id), None)
        psychiatrist = next(
            (item for item in psychiatrists if item.get("psychiatrist_id") == request.psychiatrist_id),
            None,
        )
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        if patient.get("status") != "Pending_Assignment":
            raise HTTPException(status_code=409, detail="Patient is not pending assignment")
        if psychiatrist is None:
            raise HTTPException(status_code=404, detail="Psychiatrist not found")
        if psychiatrist.get("status") in ("Inactive", "Offline"):
            raise HTTPException(status_code=409, detail="Psychiatrist is currently inactive")

        patient["assigned_psychiatrist_id"] = request.psychiatrist_id
        patient["status"] = "Active"
        psychiatrist["status"] = "Active"
        patient["assigned_at"] = datetime.now(timezone.utc).isoformat()
        write_json("patients.json", patients)
        write_json("psychiatrists.json", psychiatrists)

    # Notify patient via Telegram
    try:
        notice = (
            f"Good news! An administrator has assigned {psychiatrist['full_name']} "
            f"({psychiatrist.get('field', 'Psychiatry')}) to your case.\n\n"
            f"You can now send messages directly in this chat to begin your consultation."
        )
        await send_telegram_message(request.telegram_id, notice)
    except Exception:
        pass

    return {"status": "assigned", "patient": patient}

