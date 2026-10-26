import hmac
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from fastapi import APIRouter, Header, HTTPException, Request

from backend.database import read_json, transaction, write_json
from backend.telegram_client import send_telegram_message

logger = logging.getLogger("telegram_router")
router = APIRouter(tags=["telegram"])
_intake_sessions: dict[int, dict[str, Any]] = {}


async def _respond(chat_id: int, text: str) -> dict[str, Any]:
    """Send text to the Telegram chat and return standard OK response."""
    try:
        await send_telegram_message(chat_id, text)
    except Exception as exc:
        logger.error("Failed to deliver Telegram reply to chat %s: %s", chat_id, exc)
    return {"ok": True}


@router.post("/api/telegram-webhook")
async def telegram_webhook(
    request: Request,
    secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, Any]:
    expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    
    # If a secret is configured, verify it (accepting matching secret or internal loop)
    if expected_secret:
        if secret_token is None or not hmac.compare_digest(secret_token, expected_secret):
            raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")

    try:
        update = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram update JSON") from exc

    message = update.get("message") if isinstance(update, dict) else None
    if not isinstance(message, dict) or not isinstance(message.get("text"), str):
        return {"ok": True, "ignored": True}

    sender = message.get("from")
    chat = message.get("chat")
    text = message["text"].strip()
    if not isinstance(sender, dict) or not isinstance(chat, dict) or not text:
        return {"ok": True, "ignored": True}

    telegram_id = sender.get("id")
    chat_id = chat.get("id")
    if not isinstance(telegram_id, int) or not isinstance(chat_id, int):
        return {"ok": True, "ignored": True}

    username = sender.get("username")
    username = username if isinstance(username, str) else ""

    patients = read_json("patients.json")
    existing_patient = next((item for item in patients if item.get("telegram_id") == telegram_id), None)

    # Cancel / Reset command
    if text in ("/cancel", "/reset"):
        _intake_sessions.pop(telegram_id, None)
        return await _respond(
            chat_id,
            "Intake canceled. Type /start whenever you are ready to begin again.",
        )

    # /start command
    if text.startswith("/start"):
        if existing_patient is not None and existing_patient.get("status") == "Active":
            return await _respond(
                chat_id,
                "Your case is active. Send a message here to continue the conversation with your psychiatrist.",
            )
        if existing_patient is not None and existing_patient.get("status") == "Pending_Assignment":
            return await _respond(
                chat_id,
                "Your intake has already been received and is being reviewed. An administrator will connect you with a psychiatrist shortly.",
            )
        _intake_sessions[telegram_id] = {"step": "name", "username": username}
        return await _respond(
            chat_id,
            "Hello! Welcome to our confidential tele-psychiatry service.\n\n"
            "To get started, please tell us: What name or pseudonym would you like to be addressed by?",
        )

    # In active session or pending
    session = _intake_sessions.get(telegram_id)
    if session is None:
        if existing_patient is not None and existing_patient.get("status") == "Active":
            psychiatrist_id = existing_patient.get("assigned_psychiatrist_id")
            with transaction():
                messages = read_json("messages.json")
                messages.append(
                    {
                        "message_id": max((item.get("message_id", 0) for item in messages), default=0) + 1,
                        "telegram_id": telegram_id,
                        "psychiatrist_id": psychiatrist_id,
                        "sender_type": "patient",
                        "text": text[:4000],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "telegram_message_id": message.get("message_id"),
                        "edited_at": None,
                        "deleted_at": None,
                        "deleted_for_psychiatrist": False,
                    }
                )
                write_json("messages.json", messages)
            return {"ok": True}

        if existing_patient is not None and existing_patient.get("status") == "Pending_Assignment":
            return await _respond(
                chat_id,
                "Your intake is being reviewed by our administration team. You will be connected with a psychiatrist shortly.",
            )

        # First message without /start: initiate intake
        _intake_sessions[telegram_id] = {"step": "name", "username": username}
        return await _respond(
            chat_id,
            "Welcome! To begin confidential intake, what name or pseudonym would you like to be addressed by?",
        )

    # Step: Name
    if session["step"] == "name":
        session["name"] = text[:200]
        session["step"] = "age"
        return await _respond(chat_id, f"Thank you, {session['name']}. How old are you?")

    # Step: Age
    if session["step"] == "age":
        try:
            age = int(text)
        except ValueError:
            return await _respond(chat_id, "Please enter your age as a number (e.g., 28).")
        if not 1 <= age <= 120:
            return await _respond(chat_id, "Please enter a valid age between 1 and 120.")
        session["age"] = age
        session["step"] = "complaint"
        return await _respond(
            chat_id,
            "Got it. Finally, please briefly describe what kind of support or concern you would like to discuss with a psychiatrist today?",
        )

    # Step: Complaint / Primary Concern
    if session["step"] == "complaint":
        with transaction():
            patients = read_json("patients.json")
            patient = next((item for item in patients if item.get("telegram_id") == telegram_id), None)
            if patient is None:
                patient = {"telegram_id": telegram_id, "created_at": datetime.now(timezone.utc).isoformat()}
                patients.append(patient)
            patient.update(
                {
                    "telegram_username": session.get("username", "") or username,
                    "name": session["name"],
                    "age": session["age"],
                    "complaint": text[:4000],
                    "status": "Pending_Assignment",
                    "assigned_psychiatrist_id": None,
                }
            )
            write_json("patients.json", patients)

        _intake_sessions.pop(telegram_id, None)
        return await _respond(
            chat_id,
            "✅ Intake complete! Your information has been securely submitted.\n\n"
            "An administrator will review your case and connect you with an available psychiatrist shortly. "
            "You will receive a notification here once your session starts.",
        )

    return await _respond(
        chat_id,
        "Your intake is already in progress. Please complete the requested information or send /cancel to restart.",
    )
