from datetime import datetime, timezone
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException

from backend.database import read_json, transaction, write_json
from backend.schemas import ChatMessageRequest
from backend.security import User, require_role


router = APIRouter(prefix="/api/chat", tags=["chat"])


def _verify_assignment(telegram_id: int, psychiatrist_id: int) -> dict[str, Any]:
    patient = next(
        (item for item in read_json("patients.json") if item.get("telegram_id") == telegram_id),
        None,
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.get("status") != "Active" or patient.get("assigned_psychiatrist_id") != psychiatrist_id:
        raise HTTPException(status_code=403, detail="Patient is not assigned to this psychiatrist")
    return patient


@router.get("/{telegram_id}/{psychiatrist_id}")
def get_chat(
    telegram_id: int,
    psychiatrist_id: int,
    user: User = Depends(require_role("Psychiatrist")),
) -> list[dict[str, Any]]:
    if psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only view your own chats")
    _verify_assignment(telegram_id, psychiatrist_id)
    messages = [
        message
        for message in read_json("messages.json")
        if message.get("telegram_id") == telegram_id
        and message.get("psychiatrist_id") == psychiatrist_id
    ]
    return sorted(messages, key=lambda message: message.get("timestamp", ""))


@router.post("/send")
async def send_chat_message(
    request: ChatMessageRequest,
    user: User = Depends(require_role("Psychiatrist")),
) -> dict[str, Any]:
    if request.psychiatrist_id != user.psychiatrist_id:
        raise HTTPException(status_code=403, detail="You can only send messages as yourself")
    _verify_assignment(request.telegram_id, request.psychiatrist_id)
    from backend.telegram_client import send_telegram_message
    try:
        await send_telegram_message(request.telegram_id, request.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not deliver message to Telegram: {exc}") from exc

    with transaction():
        messages = read_json("messages.json")
        message = {
            "message_id": max((item.get("message_id", 0) for item in messages), default=0) + 1,
            "telegram_id": request.telegram_id,
            "psychiatrist_id": request.psychiatrist_id,
            "sender_type": "psychiatrist",
            "text": request.text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        messages.append(message)
        write_json("messages.json", messages)
    return message
