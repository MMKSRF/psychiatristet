import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("telegram_polling")
API_URL = os.getenv("CAREBRIDGE_API_URL", "http://127.0.0.1:8000").rstrip("/")
POLL_TIMEOUT_SECONDS = 25


async def _telegram_request(
    client: httpx.AsyncClient,
    token: str,
    method: str,
    **payload: Any,
) -> dict[str, Any]:
    response = await client.post(
        f"https://api.telegram.org/bot{token}/{method}",
        json=payload,
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError(f"Telegram {method} request was rejected: {result}")
    return result


async def run_polling_loop(asgi_app: Any = None) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set; Telegram poller disabled.")
        return

    offset: int | None = None
    telegram_timeout = httpx.Timeout(POLL_TIMEOUT_SECONDS + 10)

    # If an ASGI app is provided, use in-memory ASGITransport, otherwise use HTTP client
    if asgi_app is not None:
        internal_transport = httpx.ASGITransport(app=asgi_app)
        api_base_url = "http://localhost"
    else:
        internal_transport = None
        api_base_url = API_URL

    logger.info("Telegram background polling worker started.")
    print("Telegram background polling worker started and listening for patients.")

    async with httpx.AsyncClient(timeout=telegram_timeout) as tg_client, \
               httpx.AsyncClient(transport=internal_transport, base_url=api_base_url, timeout=30.0) as api_client:
        while True:
            try:
                updates = await _telegram_request(
                    tg_client,
                    token,
                    "getUpdates",
                    offset=offset,
                    timeout=POLL_TIMEOUT_SECONDS,
                    allowed_updates=["message"],
                )

                for update in updates.get("result", []):
                    if not isinstance(update, dict):
                        continue
                    update_id = update.get("update_id")
                    if not isinstance(update_id, int):
                        continue

                    headers = {}
                    if webhook_secret:
                        headers["X-Telegram-Bot-Api-Secret-Token"] = webhook_secret

                    response = await api_client.post(
                        "/api/telegram-webhook" if asgi_app else f"{API_URL}/api/telegram-webhook",
                        headers=headers,
                        json=update,
                    )
                    response.raise_for_status()
                    offset = update_id + 1

                    # Backward compatibility for any remaining sendMessage webhook reply
                    action = response.json()
                    if isinstance(action, dict) and action.get("method") == "sendMessage":
                        await _telegram_request(
                            tg_client,
                            token,
                            "sendMessage",
                            chat_id=action["chat_id"],
                            text=action["text"],
                        )

            except asyncio.CancelledError:
                logger.info("Telegram polling loop cancelled.")
                break
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if exc.request.url.host == "api.telegram.org":
                    logger.warning("Telegram returned HTTP %s. Webhook might be active.", status)
                else:
                    logger.warning("CareBridge API returned HTTP %s.", status)
                await asyncio.sleep(3)
            except Exception as exc:
                logger.warning("Telegram polling error (%s): %s", type(exc).__name__, exc)
                await asyncio.sleep(3)


async def poll() -> None:
    await run_polling_loop(asgi_app=None)


if __name__ == "__main__":
    try:
        asyncio.run(poll())
    except KeyboardInterrupt:
        print("\nTelegram polling stopped.")
