#!/usr/bin/env python3
"""CareBridge Telehealth MVP - Production & Remote Server Launcher

Starts the FastAPI server bound to 0.0.0.0 so clients on external networks,
mobile phones, and remote browsers can connect via the server's public IP:
http://204.44.66.142:8000
"""
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
root_dir = Path(__file__).resolve().parent
load_dotenv(root_dir / ".env")

# Ensure Python path includes project root
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.database import DB_PATH, get_connection, init_db


def print_server_banner(server_ip: str, port: int, reload: bool) -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    masked_token = f"{bot_token[:10]}...{bot_token[-6:]}" if len(bot_token) > 16 else "[NOT SET]"

    # Quick db stats
    try:
        with get_connection() as conn:
            p_count = conn.execute("SELECT count(*) FROM patients;").fetchone()[0]
            d_count = conn.execute("SELECT count(*) FROM psychiatrists;").fetchone()[0]
            m_count = conn.execute("SELECT count(*) FROM messages;").fetchone()[0]
            db_stats = f"{p_count} patients, {d_count} clinicians, {m_count} messages"
    except Exception:
        db_stats = "Ready"

    db_rel = os.path.relpath(DB_PATH, root_dir) if DB_PATH.is_relative_to(root_dir) else str(DB_PATH)

    print("\n" + "=" * 70)
    print("   🏥 CareBridge Telehealth Server - Remote & Mobile Network")
    print("=" * 70)
    print(f"🌍 Server Public IP:    {server_ip}")
    print(f"📱 Phone Web Dashboard: http://{server_ip}:{port}")
    print(f"💻 Login URL:           http://{server_ip}:{port}/login")
    print(f"📚 Swagger API Docs:    http://{server_ip}:{port}/docs")
    print(f"🗄️  Database File:       {db_rel} ({db_stats})")
    print(f"🤖 Telegram Bot:        @psychiatristETbot ({masked_token})")
    print(f"⚡ Server Mode:         host=0.0.0.0, port={port}, reload={reload}")
    print("-" * 70)
    print("🔑 Demo Credentials:")
    print("   - Admin:       username: admin      password: hYetbUdypvojTIMdosA7mxHq")
    print("   - Clinician 1: username: clinician  password: eegdZKsvX6ldqvDsm8cxqzIe")
    print("   - Clinician 2: username: clinician2 password: samLeePassword123")
    print("-" * 70)
    print("📱 Mobile Phone Testing Instructions:")
    print(f"   1. Open Chrome/Safari on your phone connected to mobile data or Wi-Fi.")
    print(f"   2. Enter: http://{server_ip}:{port}")
    print("   3. Log in as clinician or admin to view active chats & patient notes.")
    print("   4. If page does not load, verify your VPS firewall allows port 8000:")
    print(f"      sudo ufw allow {port}/tcp")
    print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="CareBridge Server Launcher for Remote / Mobile Access")
    parser.add_argument(
        "--ip",
        default=os.getenv("SERVER_IP", "204.44.66.142"),
        help="Public server IP address (default: 204.44.66.142)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0 for external network access)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("RELOAD", "false").lower() in ("true", "1"),
        help="Enable auto-reload (leave disabled on 1GB RAM server to save memory)",
    )

    args = parser.parse_args()

    # Ensure database is initialized before uvicorn launches
    init_db()

    # Ensure CORS allows server IP and all network interfaces
    existing_cors = os.getenv("CORS_ORIGINS", "")
    server_urls = f"http://{args.ip}:{args.port},http://{args.ip},http://localhost:{args.port},http://127.0.0.1:{args.port}"
    if server_urls not in existing_cors:
        os.environ["CORS_ORIGINS"] = f"{existing_cors},{server_urls}".strip(",")

    print_server_banner(server_ip=args.ip, port=args.port, reload=args.reload)

    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        access_log=True,
    )


if __name__ == "__main__":
    main()

