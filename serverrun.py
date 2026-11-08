#!/usr/bin/env python3
"""CareBridge Telehealth MVP - Production Server Launcher (Backend-Only)

Runs ONLY the FastAPI backend on 0.0.0.0:8000.  The React frontend is
served directly from the pre-built  frontend/dist/  folder — no Node.js,
npm, or Vite required on the production server.

Usage (on VPS):
    python3 serverrun.py                   # defaults: 0.0.0.0:8000
    python3 serverrun.py --port 8080
    python3 serverrun.py --ip 204.44.66.142 --port 8000

The script loads .env from the project root so all credentials are
available to the FastAPI application even when uvicorn is started as a
sub-process module.
"""
import argparse
import os
import sys
from pathlib import Path

# ── 1. Resolve project root and load .env ────────────────────────────────────
root_dir = Path(__file__).resolve().parent

# Try multiple locations (handles different CWDs on the server)
_env_candidates = [
    root_dir / ".env",
    Path.cwd() / ".env",
]
try:
    from dotenv import load_dotenv
    for _c in _env_candidates:
        if _c.is_file():
            load_dotenv(_c, override=False)
            break
except ImportError:
    pass  # python-dotenv not installed; rely on env vars set by the shell

# ── 2. Add project root to sys.path so "backend.*" imports work ───────────────
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# ── 3. Initialise SQLite database before uvicorn starts ───────────────────────
from backend.database import init_db, DB_PATH, get_connection  # noqa: E402
init_db()


def _db_stats() -> str:
    try:
        with get_connection() as conn:
            p = conn.execute("SELECT count(*) FROM patients;").fetchone()[0]
            d = conn.execute("SELECT count(*) FROM psychiatrists;").fetchone()[0]
            m = conn.execute("SELECT count(*) FROM messages;").fetchone()[0]
            return f"{p} patients, {d} clinicians, {m} messages"
    except Exception:
        return "ready"


def _banner(ip: str, port: int) -> None:
    db_rel = os.path.relpath(DB_PATH, root_dir) if DB_PATH.is_relative_to(root_dir) else str(DB_PATH)
    tok = os.getenv("TELEGRAM_BOT_TOKEN", "")
    masked = f"{tok[:10]}...{tok[-6:]}" if len(tok) > 16 else "[NOT SET]"
    sep = "=" * 68
    print(f"\n{sep}")
    print("   🏥  CareBridge Telehealth — Production Server")
    print(sep)
    print(f"🌍  Server IP:          {ip}")
    print(f"💻  Web Dashboard:      http://{ip}:{port}")
    print(f"🔑  Login URL:          http://{ip}:{port}/login")
    print(f"📚  API Docs:           http://{ip}:{port}/docs")
    print(f"🗄️   Database:           {db_rel}  ({_db_stats()})")
    print(f"🤖  Telegram Bot:       @psychiatristETbot  ({masked})")
    print("-" * 68)
    print("🔑  Demo Credentials:")
    print("    Admin:       username: admin       password: hYetbUdypvojTIMdosA7mxHq")
    print("    Clinician 1: username: clinician   password: eegdZKsvX6ldqvDsm8cxqzIe")
    print("    Clinician 2: username: clinician2  password: samLeePassword123")
    print(sep + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CareBridge production server (backend only — React served from dist/)"
    )
    parser.add_argument(
        "--ip",
        default=os.getenv("SERVER_IP", "204.44.66.142"),
        help="Public server IP shown in the banner (default: 204.44.66.142)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of uvicorn worker processes (default: 1 — keep at 1 for 1 GB RAM)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload (dev only — do NOT use on production server)",
    )
    args = parser.parse_args()

    # Extend CORS to cover the server IP on this port
    cors_set = {
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "").split(",")
        if o.strip()
    }
    cors_set.update({
        f"http://{args.ip}:{args.port}",
        f"http://{args.ip}",
        f"http://localhost:{args.port}",
        f"http://127.0.0.1:{args.port}",
        "http://localhost:5173",
        "http://localhost:3000",
    })
    os.environ["CORS_ORIGINS"] = ",".join(sorted(cors_set))

    _banner(args.ip, args.port)

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
        access_log=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
