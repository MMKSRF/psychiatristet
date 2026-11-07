from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.database import (
    add_message,
    create_patient_note,
    delete_message,
    delete_patient_note,
    edit_message,
    get_chat_messages,
    get_message,
    get_patient,
    get_patient_notes,
    update_patient_note,
)
from backend.schemas import (
    ChatMessage,
    ChatMessageRequest,
    EditChatMessageRequest,
    PatientNote,
    PatientNoteRequest,
)
from backend.security import User, require_role
from backend.telegram_client import delete_telegram_message, edit_telegram_message, send_telegram_message


router = APIRouter(prefix="/api/chat", tags=["chat"])


def _verify_assignment(telegram_id: int, psychiatrist_id: int) -> dict[str, Any]:
    patient = get_patient(telegram_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.get("status") != "Active" or patient.get("assigned_psychiatrist_id") != psychiatrist_id:
        raise HTTPException(status_code=403, detail="Patient is not assigned to this psychiatrist")
    return patient


def _find_scoped_message(
    message_id: int,
    telegram_id: int,
    psychiatrist_id: int,
) -> dict[str, Any]:
    message = get_message(message_id, telegram_id, psychiatrist_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.get("sender_type") != "psychiatrist":
        raise HTTPException(status_code=403, detail="Only clinician-authored messages can be changed")
    if message.get("deleted_at") is not None or message.get("deleted_for_psychiatrist") is True:
        raise HTTPException(status_code=409, detail="This message has already been deleted")
    return message


@router.get("/{telegram_id}/{psychiatrist_id}/notes", response_model=list[PatientNote])
def list_patient_notes(
    telegram_id: int,
    psychiatrist_id: int,
    user: User = Depends(require_role("Psychiatrist")),
) -> list[dict[str, Any]]:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only view your own patient notes")
    _verify_assignment(telegram_id, psychiatrist_id)
    return get_patient_notes(telegram_id, psychiatrist_id)


@router.post("/{telegram_id}/{psychiatrist_id}/notes", status_code=201, response_model=PatientNote)
def create_note_endpoint(
    telegram_id: int,
    psychiatrist_id: int,
    request: PatientNoteRequest,
    user: User = Depends(require_role("Psychiatrist")),
) -> dict[str, Any]:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only create your own patient notes")
    _verify_assignment(telegram_id, psychiatrist_id)
    return create_patient_note(telegram_id, psychiatrist_id, request.text)


@router.patch("/{telegram_id}/{psychiatrist_id}/notes/{note_id}", response_model=PatientNote)
def update_note_endpoint(
    telegram_id: int,
    psychiatrist_id: int,
    note_id: int,
    request: PatientNoteRequest,
    user: User = Depends(require_role("Psychiatrist")),
) -> dict[str, Any]:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only edit your own patient notes")
    _verify_assignment(telegram_id, psychiatrist_id)
    note = update_patient_note(note_id, telegram_id, psychiatrist_id, request.text)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/{telegram_id}/{psychiatrist_id}/notes/{note_id}", status_code=204)
def delete_note_endpoint(
    telegram_id: int,
    psychiatrist_id: int,
    note_id: int,
    user: User = Depends(require_role("Psychiatrist")),
) -> None:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only delete your own patient notes")
    _verify_assignment(telegram_id, psychiatrist_id)
    if not delete_patient_note(note_id, telegram_id, psychiatrist_id):
        raise HTTPException(status_code=404, detail="Note not found")


@router.get("/{telegram_id}/{psychiatrist_id}", response_model=list[ChatMessage])
def get_chat(
    telegram_id: int,
    psychiatrist_id: int,
    user: User = Depends(require_role("Psychiatrist")),
) -> list[dict[str, Any]]:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only view your own chats")
    _verify_assignment(telegram_id, psychiatrist_id)
    return get_chat_messages(telegram_id, psychiatrist_id)


@router.post("/send", response_model=ChatMessage)
async def send_chat_message(
    request: ChatMessageRequest,
    user: User = Depends(require_role("Psychiatrist")),
) -> dict[str, Any]:
    if request.psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only send messages as yourself")
    _verify_assignment(request.telegram_id, request.psychiatrist_id)
    try:
        telegram_result = await send_telegram_message(request.telegram_id, request.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not deliver message to Telegram: {exc}") from exc

    telegram_message = telegram_result.get("result", {}) if isinstance(telegram_result, dict) else {}
    return add_message(
        {
            "telegram_id": request.telegram_id,
            "psychiatrist_id": request.psychiatrist_id,
            "sender_type": "psychiatrist",
            "text": request.text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "telegram_message_id": telegram_message.get("message_id") if isinstance(telegram_message, dict) else None,
            "edited_at": None,
            "deleted_at": None,
            "deleted_for_psychiatrist": False,
        }
    )


@router.patch("/{telegram_id}/{psychiatrist_id}/{message_id}", response_model=ChatMessage)
async def edit_chat_message(
    telegram_id: int,
    psychiatrist_id: int,
    message_id: int,
    request: EditChatMessageRequest,
    user: User = Depends(require_role("Psychiatrist")),
) -> dict[str, Any]:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only edit your own messages")
    _verify_assignment(telegram_id, psychiatrist_id)
    message = _find_scoped_message(message_id, telegram_id, psychiatrist_id)
    telegram_message_id = message.get("telegram_message_id")
    if not isinstance(telegram_message_id, int):
        raise HTTPException(
            status_code=409,
            detail="This older message has no Telegram message ID and cannot be edited remotely",
        )
    try:
        await edit_telegram_message(telegram_id, telegram_message_id, request.text)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Telegram could not edit this message: {exc}",
        ) from exc

    updated = edit_message(message_id, telegram_id, psychiatrist_id, request.text)
    if not updated:
        raise HTTPException(status_code=404, detail="Message not found")
    return updated


@router.delete("/{telegram_id}/{psychiatrist_id}/{message_id}")
async def delete_chat_message(
    telegram_id: int,
    psychiatrist_id: int,
    message_id: int,
    scope: str = Query(pattern="^(self|everyone)$"),
    user: User = Depends(require_role("Psychiatrist")),
) -> dict[str, str]:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")
    _verify_assignment(telegram_id, psychiatrist_id)
    message = _find_scoped_message(message_id, telegram_id, psychiatrist_id)
    if scope == "everyone":
        telegram_message_id = message.get("telegram_message_id")
        if isinstance(telegram_message_id, int):
            try:
                await delete_telegram_message(telegram_id, telegram_message_id)
            except Exception as exc:
                print(f"[Telegram] Note: deleteMessage: {exc}")

    delete_message(message_id, telegram_id, psychiatrist_id, scope)
    return {"status": "deleted", "scope": scope}
