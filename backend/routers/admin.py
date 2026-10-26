from datetime import datetime, timezone
import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.database import read_json, transaction, write_json
from backend.schemas import AssignCaseRequest, CreatePsychiatristRequest, UpdateCapacityRequest
from backend.security import User, hash_password, require_role
from backend.telegram_client import send_telegram_message


router = APIRouter(prefix="/api/admin", tags=["admin"])
DEFAULT_PATIENT_CAPACITY = 5


def _public_psychiatrist(
    psychiatrist: dict[str, Any],
    patients: list[dict[str, Any]],
) -> dict[str, Any]:
    assigned = [
        patient
        for patient in patients
        if patient.get("assigned_psychiatrist_id") == psychiatrist.get("psychiatrist_id")
        and patient.get("status") == "Active"
    ]
    return {
        key: value
        for key, value in psychiatrist.items()
        if key not in {"password", "password_hash", "initial_password"}
    } | {
        "max_patients": psychiatrist.get("max_patients", DEFAULT_PATIENT_CAPACITY),
        "assigned_patient_count": len(assigned),
    }


@router.get("/pending-patients")
def pending_patients(_: User = Depends(require_role("Admin"))) -> list[dict[str, Any]]:
    return [
        patient
        for patient in read_json("patients.json")
        if patient.get("status") == "Pending_Assignment"
    ]


@router.get("/psychiatrists")
def psychiatrists(_: User = Depends(require_role("Admin"))) -> list[dict[str, Any]]:
    patients = read_json("patients.json")
    return [
        _public_psychiatrist(psychiatrist, patients)
        for psychiatrist in read_json("psychiatrists.json")
    ]


@router.post("/psychiatrists", status_code=201)
def create_psychiatrist(
    request: CreatePsychiatristRequest,
    _: User = Depends(require_role("Admin")),
) -> dict[str, Any]:
    configured_users_raw = os.getenv("AUTH_USERS_JSON", "[]")
    try:
        configured_users = json.loads(configured_users_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail="AUTH_USERS_JSON is not valid JSON") from exc
    if not isinstance(configured_users, list):
        raise HTTPException(status_code=503, detail="AUTH_USERS_JSON must be a list")
    for account in configured_users:
        if not isinstance(account, dict):
            continue
        username = account.get("username")
        if isinstance(username, str) and username.casefold() == request.email:
            if account.get("role") != "Psychiatrist":
                raise HTTPException(status_code=409, detail="This email is already assigned to a non-clinician account")
            raise HTTPException(status_code=409, detail="A psychiatrist with this email is already configured")
    with transaction():
        psychiatrists = read_json("psychiatrists.json")
        if any(
            request.email == str(item.get("email", item.get("username", ""))).casefold()
            for item in psychiatrists
        ):
            raise HTTPException(status_code=409, detail="A psychiatrist with this email already exists")
        psychiatrist_id = max(
            (item.get("psychiatrist_id", 0) for item in psychiatrists if isinstance(item.get("psychiatrist_id"), int)),
            default=0,
        ) + 1
        psychiatrist = {
            "psychiatrist_id": psychiatrist_id,
            "username": request.email,
            "email": request.email,
            "full_name": request.full_name,
            "field": request.field,
            "status": "Active",
            "max_patients": DEFAULT_PATIENT_CAPACITY,
            "password_hash": hash_password(request.initial_password),
            "must_change_password": True,
        }
        psychiatrists.append(psychiatrist)
        write_json("psychiatrists.json", psychiatrists)
    return _public_psychiatrist(psychiatrist, read_json("patients.json"))


@router.patch("/psychiatrists/{psychiatrist_id}/capacity")
def update_capacity(
    psychiatrist_id: int,
    request: UpdateCapacityRequest,
    _: User = Depends(require_role("Admin")),
) -> dict[str, Any]:
    with transaction():
        patients = read_json("patients.json")
        psychiatrists = read_json("psychiatrists.json")
        psychiatrist = next(
            (item for item in psychiatrists if item.get("psychiatrist_id") == psychiatrist_id),
            None,
        )
        if psychiatrist is None:
            raise HTTPException(status_code=404, detail="Psychiatrist not found")
        assigned_count = sum(
            patient.get("assigned_psychiatrist_id") == psychiatrist_id
            and patient.get("status") == "Active"
            for patient in patients
        )
        if request.max_patients < assigned_count:
            raise HTTPException(
                status_code=409,
                detail=f"Capacity cannot be lower than the {assigned_count} currently assigned active patients",
            )
        psychiatrist["max_patients"] = request.max_patients
        write_json("psychiatrists.json", psychiatrists)
    return _public_psychiatrist(psychiatrist, patients)


@router.get("/psychiatrists/{psychiatrist_id}/patients")
def psychiatrist_patients(
    psychiatrist_id: int,
    _: User = Depends(require_role("Admin")),
) -> list[dict[str, Any]]:
    if not any(
        item.get("psychiatrist_id") == psychiatrist_id
        for item in read_json("psychiatrists.json")
    ):
        raise HTTPException(status_code=404, detail="Psychiatrist not found")
    return [
        patient
        for patient in read_json("patients.json")
        if patient.get("assigned_psychiatrist_id") == psychiatrist_id
        and patient.get("status") == "Active"
    ]


@router.get("/interaction-logs")
def interaction_logs(_: User = Depends(require_role("Admin"))) -> list[dict[str, Any]]:
    patients = {item.get("telegram_id"): item for item in read_json("patients.json")}
    psychiatrists = {
        item.get("psychiatrist_id"): item for item in read_json("psychiatrists.json")
    }
    summaries: dict[tuple[int, int], dict[str, Any]] = {}
    for message in read_json("messages.json"):
        telegram_id = message.get("telegram_id")
        psychiatrist_id = message.get("psychiatrist_id")
        if not isinstance(telegram_id, int) or not isinstance(psychiatrist_id, int):
            continue
        key = (telegram_id, psychiatrist_id)
        summary = summaries.setdefault(
            key,
            {
                "telegram_id": telegram_id,
                "patient_name": patients.get(telegram_id, {}).get("name", "Unknown patient"),
                "psychiatrist_id": psychiatrist_id,
                "psychiatrist_name": psychiatrists.get(psychiatrist_id, {}).get("full_name", "Unknown psychiatrist"),
                "message_count": 0,
                "patient_message_count": 0,
                "psychiatrist_message_count": 0,
                "last_message_at": None,
            },
        )
        summary["message_count"] += 1
        sender_type = message.get("sender_type")
        if sender_type == "patient":
            summary["patient_message_count"] += 1
        elif sender_type == "psychiatrist":
            summary["psychiatrist_message_count"] += 1
        timestamp = message.get("timestamp")
        if isinstance(timestamp, str) and (
            summary["last_message_at"] is None or timestamp > summary["last_message_at"]
        ):
            summary["last_message_at"] = timestamp
    return sorted(
        summaries.values(),
        key=lambda item: item["last_message_at"] or "",
        reverse=True,
    )


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
        current_count = sum(
            assigned.get("assigned_psychiatrist_id") == request.psychiatrist_id
            and assigned.get("status") == "Active"
            for assigned in patients
        )
        capacity = psychiatrist.get("max_patients", DEFAULT_PATIENT_CAPACITY)
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            capacity = DEFAULT_PATIENT_CAPACITY
        if current_count >= capacity:
            raise HTTPException(
                status_code=409,
                detail=f"Psychiatrist has reached their patient capacity of {capacity}",
            )

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
