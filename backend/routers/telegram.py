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

from backend.database import add_message, get_patient, update_patient_language, upsert_patient
from backend.telegram_client import answer_callback_query, send_telegram_message

logger = logging.getLogger("telegram_router")
router = APIRouter(tags=["telegram"])
_intake_sessions: dict[int, dict[str, Any]] = {}

LANGUAGE_KEYBOARD = {
    "keyboard": [
        [{"text": "🇪🇹 አማርኛ"}, {"text": "🇬🇧 English"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}

REMOVE_KEYBOARD = {"remove_keyboard": True}

WELCOME_TEXT = (
    "👋 Welcome to KUECSF Counseling / እንኳን ወደ KUECSF  counseling በደህና መጡ!\n\n"
    "እባክዎ የመገናኛ ቋንቋዎን ይምረጡ፦\n"
    "Please choose your preferred language:"
)

INVALID_LANG_CHOICE_TEXT = (
    "እባክዎ ከታች ካሉት አማራጮች አንዱን ይምረጡ / Please choose one of the options below:\n\n"
    "1. 🇪🇹 አማርኛ\n"
    "2. 🇬🇧 English"
)

PROMPT_NAME_TEXT = {
    "am": "እናመሰግናለን! አማርኛ ተመርጧል።\n\nለመጀመር እባክዎ እንዲጠሩበት የሚፈልጉትን ስም ወይም መጠሪያ ይንገሩን፦",
    "en": "Thank you! English selected.\n\nTo get started, please tell us: What name or pseudonym would you like to be addressed by?",
}

INVALID_AGE_NUMBER_TEXT = {
    "am": "እባክዎ እድሜዎን በቁጥር ብቻ ያስገቡ (ለምሳሌ 28)።",
    "en": "Please enter your age as a number (e.g., 28).",
}

INVALID_AGE_RANGE_TEXT = {
    "am": "እባክዎ ትክክለኛ እድሜ በ1 እና 120 መካከል ያስገቡ።",
    "en": "Please enter a valid age between 1 and 120.",
}

PROMPT_COMPLAINT_TEXT = {
    "am": "ተረድተናል። በመጨረሻም፣ ዛሬ ከአእምሮ ሐኪም ጋር መወያየት የሚፈልጉትን ችግር ወይም የድጋፍ አይነት ባጭሩ ያብራሩልን፦",
    "en": "Got it. Finally, please briefly describe what kind of support or concern you would like to discuss with a psychiatrist today?",
}

INTAKE_COMPLETE_TEXT = {
    "am": (
        "✅ መረጃዎ በተሳካ ሁኔታ ተመዝግቧል!\n\n"
        "አስተዳዳሪው ሁኔታዎን አይቶ በቅርቡ ከአእምሮ ሐኪም ጋር ያገናኝዎታል። "
        "ክፍለ-ጊዜዎ ሲጀምር እዚህ ማሳወቂያ ይደርስዎታል።"
    ),
    "en": (
        "✅ Intake complete! Your information has been securely submitted.\n\n"
        "An administrator will review your case and connect you with an available psychiatrist shortly. "
        "You will receive a notification here once your session starts."
    ),
}

ACTIVE_CASE_TEXT = {
    "am": "ጉዳይዎ ገቢር (active) ነው። ከሐኪምዎ ጋር ንግግሩን ለመቀጠል እዚህ መልዕክት ይላኩ።",
    "en": "Your case is active. Send a message here to continue the conversation with your psychiatrist.",
}

PENDING_REVIEW_TEXT = {
    "am": "መረጃዎ ደርሶናል፣ በመገምገም ላይ ነው። አስተዳዳሪው በቅርቡ ከአእምሮ ሐኪም ጋር ያገናኝዎታል።",
    "en": "Your intake has already been received and is being reviewed. An administrator will connect you with a psychiatrist shortly.",
}

CANCEL_TEXT = {
    "am": "ምዝገባው ተሰርዟል። እንደገና ለመጀመር /start ይጻፉ።",
    "en": "Intake canceled. Type /start whenever you are ready to begin again.",
}

IN_PROGRESS_TEXT = {
    "am": "ምዝገባዎ በመካሄድ ላይ ነው። እባክዎ የተጠየቁትን መረጃ ያስገቡ ወይም እንደገና ለመጀመር /cancel ይላኩ።",
    "en": "Your intake is already in progress. Please complete the requested information or send /cancel to restart.",
}


def _parse_language(raw_text: str) -> str | None:
    t = raw_text.strip().lower()
    if "አማርኛ" in raw_text or "🇪🇹" in raw_text or "amharic" in t or t in ("am", "amh", "1", "1."):
        return "am"
    if "english" in t or "🇬🇧" in raw_text or t in ("en", "eng", "2", "2."):
        return "en"
    return None


async def _respond(chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send text to the Telegram chat and return standard OK response."""
    try:
        await send_telegram_message(chat_id, text, reply_markup=reply_markup)
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

    callback_query = update.get("callback_query") if isinstance(update, dict) else None
    message = update.get("message") if isinstance(update, dict) else None

    if callback_query and isinstance(callback_query, dict):
        cb_id = callback_query.get("id")
        if cb_id:
            try:
                await answer_callback_query(str(cb_id))
            except Exception:
                pass
        message = callback_query.get("message") or {}
        sender = callback_query.get("from")
        chat = message.get("chat") or {}
        text = str(callback_query.get("data", "")).strip()
    elif isinstance(message, dict) and isinstance(message.get("text"), str):
        sender = message.get("from")
        chat = message.get("chat")
        text = message["text"].strip()
    else:
        return {"ok": True, "ignored": True}

    if not isinstance(sender, dict) or not isinstance(chat, dict) or not text:
        return {"ok": True, "ignored": True}

    telegram_id = sender.get("id")
    chat_id = chat.get("id")
    if not isinstance(telegram_id, int) or not isinstance(chat_id, int):
        return {"ok": True, "ignored": True}

    username = sender.get("username")
    username = username if isinstance(username, str) else ""

    existing_patient = get_patient(telegram_id)

    # Cancel / Reset command
    if text in ("/cancel", "/reset"):
        session = _intake_sessions.pop(telegram_id, None)
        lang = session.get("language") if session else None
        if not lang and existing_patient:
            lang = existing_patient.get("language")
        msg = CANCEL_TEXT[lang] if lang in CANCEL_TEXT else f"{CANCEL_TEXT['am']}\n{CANCEL_TEXT['en']}"
        return await _respond(chat_id, msg, reply_markup=REMOVE_KEYBOARD)

    # Change language command
    if text.startswith(("/language", "/lang")):
        _intake_sessions[telegram_id] = {
            "step": "change_language",
            "username": username,
            "session_data": _intake_sessions.get(telegram_id),
        }
        return await _respond(
            chat_id,
            "እባክዎ የመገናኛ ቋንቋዎን ይምረጡ / Please choose your preferred language:",
            reply_markup=LANGUAGE_KEYBOARD,
        )

    # /start command
    if text.startswith("/start"):
        if existing_patient is not None and existing_patient.get("status") == "Active":
            lang = existing_patient.get("language", "am")
            return await _respond(chat_id, ACTIVE_CASE_TEXT.get(lang, ACTIVE_CASE_TEXT["en"]))
        if existing_patient is not None and existing_patient.get("status") == "Pending_Assignment":
            lang = existing_patient.get("language", "am")
            return await _respond(chat_id, PENDING_REVIEW_TEXT.get(lang, PENDING_REVIEW_TEXT["en"]))
        
        _intake_sessions[telegram_id] = {"step": "language", "username": username}
        return await _respond(chat_id, WELCOME_TEXT, reply_markup=LANGUAGE_KEYBOARD)

    # In active session or pending
    session = _intake_sessions.get(telegram_id)
    if session is None:
        if existing_patient is not None and existing_patient.get("status") == "Active":
            psychiatrist_id = existing_patient.get("assigned_psychiatrist_id")
            add_message(
                {
                    "telegram_id": telegram_id,
                    "psychiatrist_id": psychiatrist_id,
                    "sender_type": "patient",
                    "text": text[:4000],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "telegram_message_id": message.get("message_id") if isinstance(message, dict) else None,
                    "edited_at": None,
                    "deleted_at": None,
                    "deleted_for_psychiatrist": False,
                }
            )
            return {"ok": True}

        if existing_patient is not None and existing_patient.get("status") == "Pending_Assignment":
            lang = existing_patient.get("language", "am")
            return await _respond(chat_id, PENDING_REVIEW_TEXT.get(lang, PENDING_REVIEW_TEXT["en"]))

        # First message without /start: initiate language choice
        _intake_sessions[telegram_id] = {"step": "language", "username": username}
        return await _respond(chat_id, WELCOME_TEXT, reply_markup=LANGUAGE_KEYBOARD)

    # Step: Change Language
    if session.get("step") == "change_language":
        chosen_lang = _parse_language(text)
        if not chosen_lang:
            return await _respond(chat_id, INVALID_LANG_CHOICE_TEXT, reply_markup=LANGUAGE_KEYBOARD)

        if existing_patient is not None:
            update_patient_language(telegram_id, chosen_lang)

        prev_session = session.get("session_data")
        if prev_session and isinstance(prev_session, dict) and prev_session.get("step") not in (None, "language", "change_language"):
            _intake_sessions[telegram_id] = prev_session
            _intake_sessions[telegram_id]["language"] = chosen_lang
        else:
            _intake_sessions.pop(telegram_id, None)

        confirm_msg = (
            "የመገናኛ ቋንቋዎ ወደ አማርኛ ተቀይሯል።"
            if chosen_lang == "am"
            else "Your preferred language has been changed to English."
        )
        return await _respond(chat_id, confirm_msg, reply_markup=REMOVE_KEYBOARD)

    # Step: Language selection
    if session["step"] == "language":
        chosen_lang = _parse_language(text)
        if not chosen_lang:
            return await _respond(chat_id, INVALID_LANG_CHOICE_TEXT, reply_markup=LANGUAGE_KEYBOARD)
        session["language"] = chosen_lang
        session["step"] = "name"
        return await _respond(chat_id, PROMPT_NAME_TEXT[chosen_lang], reply_markup=REMOVE_KEYBOARD)

    # Step: Name
    if session["step"] == "name":
        session["name"] = text[:200]
        session["step"] = "age"
        lang = session.get("language", "am")
        if lang == "am":
            return await _respond(chat_id, f"እናመሰግናለን {session['name']}። እድሜዎ ስንት ነው?")
        return await _respond(chat_id, f"Thank you, {session['name']}. How old are you?")

    # Step: Age
    if session["step"] == "age":
        lang = session.get("language", "am")
        try:
            age = int(text)
        except ValueError:
            return await _respond(chat_id, INVALID_AGE_NUMBER_TEXT[lang])
        if not 1 <= age <= 120:
            return await _respond(chat_id, INVALID_AGE_RANGE_TEXT[lang])
        session["age"] = age
        session["step"] = "complaint"
        return await _respond(chat_id, PROMPT_COMPLAINT_TEXT[lang])

    # Step: Complaint / Primary Concern
    if session["step"] == "complaint":
        lang = session.get("language", "am")
        upsert_patient(
            {
                "telegram_id": telegram_id,
                "telegram_username": session.get("username", "") or username,
                "name": session["name"],
                "age": session["age"],
                "complaint": text[:4000],
                "language": lang,
                "status": "Pending_Assignment",
                "assigned_psychiatrist_id": None,
            }
        )

        _intake_sessions.pop(telegram_id, None)
        return await _respond(chat_id, INTAKE_COMPLETE_TEXT[lang])

    lang = session.get("language", "am")
    return await _respond(chat_id, IN_PROGRESS_TEXT[lang])
