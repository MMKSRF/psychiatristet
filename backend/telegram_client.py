import os
from pathlib import Path
from typing import Any
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_bot_token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def get_webhook_secret() -> str:
    return os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()


async def send_telegram_message(
    chat_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
    parse_mode: str | None = None,
) -> dict[str, Any]:
    token = get_bot_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode is not None:
        payload["parse_mode"] = parse_mode

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram sendMessage rejected: {data.get('description')}")
        return data


async def answer_callback_query(callback_query_id: str, text: str | None = None) -> dict[str, Any]:
    token = get_bot_token()
    if not token:
        return {"ok": False}

    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return {"ok": False}


async def edit_telegram_message(chat_id: int, message_id: int, text: str) -> dict[str, Any]:
    token = get_bot_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/editMessageText",
            json={"chat_id": chat_id, "message_id": message_id, "text": text},
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram editMessageText rejected: {data.get('description')}")
        return data


async def delete_telegram_message(chat_id: int, message_id: int) -> dict[str, Any]:
    token = get_bot_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram deleteMessage rejected: {data.get('description')}")
        return data


async def get_webhook_info() -> dict[str, Any]:
    token = get_bot_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
        response.raise_for_status()
        return response.json().get("result", {})


async def set_webhook(url: str, secret_token: str | None = None) -> dict[str, Any]:
    token = get_bot_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    payload: dict[str, Any] = {
        "url": url,
        "allowed_updates": ["message", "callback_query"],
    }
    secret = secret_token or get_webhook_secret()
    if secret:
        payload["secret_token"] = secret

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(f"https://api.telegram.org/bot{token}/setWebhook", json=payload)
        response.raise_for_status()
        return response.json()


async def delete_webhook() -> dict[str, Any]:
    token = get_bot_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/deleteWebhook",
            json={"drop_pending_updates": False},
        )
        response.raise_for_status()
        return response.json()
