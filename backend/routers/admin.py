from datetime import datetime, timezone
import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.database import (
    assign_patient,
    create_psychiatrist as db_create_psychiatrist,
    get_interaction_logs as db_get_interaction_logs,
    get_patient,
    get_patients,
    get_psychiatrist,
    get_psychiatrist_by_username,
    get_psychiatrists,
    update_psychiatrist_capacity as db_update_psychiatrist_capacity,
)
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
    return get_patients(status="Pending_Assignment")


@router.get("/psychiatrists")
def list_psychiatrists(_: User = Depends(require_role("Admin"))) -> list[dict[str, Any]]:
    patients = get_patients()
    return [
        _public_psychiatrist(psychiatrist, patients)
        for psychiatrist in get_psychiatrists()
    ]


@router.post("/psychiatrists", status_code=201)
def create_psychiatrist_endpoint(
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

    if get_psychiatrist_by_username(request.email) is not None:
        raise HTTPException(status_code=409, detail="A psychiatrist with this email already exists")

    psychiatrist = db_create_psychiatrist(
        {
            "username": request.email,
            "email": request.email,
            "full_name": request.full_name,
            "field": request.field,
            "status": "Active",
            "max_patients": DEFAULT_PATIENT_CAPACITY,
            "password_hash": hash_password(request.initial_password),
            "must_change_password": True,
        }
    )
    return _public_psychiatrist(psychiatrist, get_patients())


@router.patch("/psychiatrists/{psychiatrist_id}/capacity")
def update_capacity(
    psychiatrist_id: int,
    request: UpdateCapacityRequest,
    _: User = Depends(require_role("Admin")),
) -> dict[str, Any]:
    psychiatrist = get_psychiatrist(psychiatrist_id)
    if psychiatrist is None:
        raise HTTPException(status_code=404, detail="Psychiatrist not found")

    patients = get_patients()
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

    updated = db_update_psychiatrist_capacity(psychiatrist_id, request.max_patients)
    return _public_psychiatrist(updated, patients)


@router.get("/psychiatrists/{psychiatrist_id}/patients")
def psychiatrist_patients(
    psychiatrist_id: int,
    _: User = Depends(require_role("Admin")),
) -> list[dict[str, Any]]:
    if get_psychiatrist(psychiatrist_id) is None:
        raise HTTPException(status_code=404, detail="Psychiatrist not found")
    return get_patients(assigned_psychiatrist_id=psychiatrist_id, status="Active")


@router.get("/interaction-logs")
def interaction_logs(_: User = Depends(require_role("Admin"))) -> list[dict[str, Any]]:
    return db_get_interaction_logs()


@router.post("/assign-case")
async def assign_case(
    request: AssignCaseRequest,
    _: User = Depends(require_role("Admin")),
) -> dict[str, Any]:
    patient = get_patient(request.telegram_id)
    psychiatrist = get_psychiatrist(request.psychiatrist_id)

    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.get("status") != "Pending_Assignment":
        raise HTTPException(status_code=409, detail="Patient is not pending assignment")
    if psychiatrist is None:
        raise HTTPException(status_code=404, detail="Psychiatrist not found")
    if psychiatrist.get("status") in ("Inactive", "Offline"):
        raise HTTPException(status_code=409, detail="Psychiatrist is currently inactive")

    active_assigned = get_patients(status="Active", assigned_psychiatrist_id=request.psychiatrist_id)
    capacity = psychiatrist.get("max_patients", DEFAULT_PATIENT_CAPACITY)
    if not isinstance(capacity, int) or isinstance(capacity, bool):
        capacity = DEFAULT_PATIENT_CAPACITY
    if len(active_assigned) >= capacity:
        raise HTTPException(
            status_code=409,
            detail=f"Psychiatrist has reached their patient capacity of {capacity}",
        )

    updated_patient = assign_patient(request.telegram_id, request.psychiatrist_id)

    # Notify patient via Telegram
    try:
        lang = updated_patient.get("language", "am")
        if lang == "am":
            field_name = psychiatrist.get("field", "የአእምሮ ጤና")
            notice = (
                f"መልካም ዜና! አስተዳዳሪው ዶ/ር {psychiatrist['full_name']} "
                f"({field_name}) መድቦልዎታል።\n\n"
                f"አሁን ምክክርዎን ለመጀመር በዚህ ውይይት መልዕክት መላክ ይችላሉ።"
            )
        else:
            notice = (
                f"Good news! An administrator has assigned {psychiatrist['full_name']} "
                f"({psychiatrist.get('field', 'Psychiatry')}) to your case.\n\n"
                f"You can now send messages directly in this chat to begin your consultation."
            )
        await send_telegram_message(request.telegram_id, notice)
    except Exception:
        pass

    return {"status": "assigned", "patient": updated_patient}
