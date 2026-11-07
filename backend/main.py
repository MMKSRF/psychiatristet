import asyncio
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure .env is loaded
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from backend import database
from backend.polling import run_polling_loop
from backend.routers import admin, auth, chat, psychiatrist, telegram
from backend.telegram_client import get_webhook_info

logger = logging.getLogger("backend_main")


def initialize_data_files() -> None:
    # Initialize SQLite database (fulldb.db) with WAL mode and migrate initial data
    database.init_db()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    initialize_data_files()

    # Automatically check Telegram status and manage polling or webhook
    polling_task: asyncio.Task | None = None
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    enable_polling = os.getenv("ENABLE_EMBEDDED_POLLING", "true").lower() in ("true", "1", "yes")

    if token:
        try:
            info = await get_webhook_info()
            webhook_url = info.get("url", "")
            if webhook_url:
                print(f"[Telegram] Active Webhook detected at: {webhook_url}")
            elif enable_polling:
                print("[Telegram] No webhook registered. Launching embedded background poller...")
                polling_task = asyncio.create_task(run_polling_loop(asgi_app=application))
        except Exception as exc:
            print(f"[Telegram] Warning: Could not verify webhook status: {exc}")
            if enable_polling:
                polling_task = asyncio.create_task(run_polling_loop(asgi_app=application))

    yield

    if polling_task and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Telehealth Telegram-Web Bridge API",
    description="MVP API for patient intake and clinician chat relay.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://204.44.66.142:5173,http://204.44.66.142:8000,http://204.44.66.142",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if ("*" not in origins) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(psychiatrist.router)
app.include_router(chat.router)
app.include_router(telegram.router)

# Mount frontend/dist if available so the full web app can be used on phone without node/npm
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        if full_path.startswith(("api/", "docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404, detail="Not Found")
        target_file = frontend_dist / full_path
        if target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    def read_root() -> dict[str, str]:
        return {"status": "ok", "service": "Telehealth Bridge MVP"}
