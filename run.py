#!/usr/bin/env python3
"""CareBridge Telehealth MVP - Unified Launcher

Starts the FastAPI server (with automatic embedded Telegram bot polling/webhook)
and prints credentials, endpoints, and instructions.
"""
import os
import sys
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
root_dir = Path(__file__).resolve().parent
load_dotenv(root_dir / ".env")


def print_banner() -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    masked_token = f"{bot_token[:10]}...{bot_token[-6:]}" if len(bot_token) > 16 else "[NOT SET]"

    print("\n" + "=" * 65)
    print("   🏥 CareBridge Telehealth Telegram-Web Bridge (MVP)")
    print("=" * 65)
    print(f"📡 Backend API:         http://localhost:8000")
    print(f"📚 Interactive Swagger: http://localhost:8000/docs")
    print(f"💻 Frontend Dashboard:  http://localhost:5173")
    print(f"🤖 Telegram Bot Token:  {masked_token}")
    print(f"🤖 Bot Username:        @psychiatristETbot")
    print("-" * 65)
    print("🔑 Demo Credentials:")
    print("   - Admin:       username: admin      password: hYetbUdypvojTIMdosA7mxHq")
    print("   - Clinician 1: username: clinician  password: eegdZKsvX6ldqvDsm8cxqzIe")
    print("   - Clinician 2: username: clinician2 password: samLeePassword123")
    print("-" * 65)
    print("⚡ Webhook / Tunnel commands:")
    print("   - Check status:  python -m backend.webhook_manager status")
    print("   - Start tunnel:  python -m backend.webhook_manager tunnel")
    print("   - Set custom:    python -m backend.webhook_manager set <URL>")
    print("   - Remove:        python -m backend.webhook_manager delete")
    print("=" * 65 + "\n")


def main() -> None:
    print_banner()
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
