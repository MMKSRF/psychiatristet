import argparse
import asyncio
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from backend.telegram_client import (
    delete_webhook,
    get_bot_token,
    get_webhook_info,
    get_webhook_secret,
    set_webhook,
)


async def cmd_status() -> None:
    print("Checking Telegram Webhook status...")
    info = await get_webhook_info()
    url = info.get("url", "")
    pending = info.get("pending_update_count", 0)
    has_cert = info.get("has_custom_certificate", False)
    last_error = info.get("last_error_message")
    last_error_date = info.get("last_error_date")

    print("\n--- Telegram Webhook Status ---")
    print(f"Active URL: {url or '[None - Polling Mode Active]'}")
    print(f"Pending Updates: {pending}")
    print(f"Custom Certificate: {has_cert}")
    if last_error:
        print(f"Last Error: {last_error} (timestamp: {last_error_date})")
    print("-------------------------------\n")


async def cmd_set(url: str) -> None:
    clean_url = url.strip().rstrip("/")
    if not clean_url.endswith("/api/telegram-webhook"):
        clean_url = f"{clean_url}/api/telegram-webhook"

    if not clean_url.startswith("https://"):
        print("Error: Telegram requires an HTTPS webhook URL.", file=sys.stderr)
        sys.exit(1)

    secret = get_webhook_secret()
    print(f"Setting webhook URL to: {clean_url}")
    if secret:
        print("Using configured TELEGRAM_WEBHOOK_SECRET token.")
    res = await set_webhook(clean_url, secret)
    print(f"Result: {res.get('description', 'Success')}")


async def cmd_delete() -> None:
    print("Removing Telegram webhook...")
    res = await delete_webhook()
    print(f"Result: {res.get('description', 'Webhook deleted. Polling is now available.')}")


def cmd_tunnel(port: int = 8000) -> None:
    """Launch cloudflared quick tunnel and automatically set Telegram webhook."""
    print(f"Starting cloudflared tunnel to localhost:{port}...")
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print("Error: 'cloudflared' command not found. Install via: brew install cloudflared", file=sys.stderr)
        sys.exit(1)

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    print("Waiting for Cloudflare Tunnel public URL...")

    start_time = time.time()
    while time.time() - start_time < 30:
        line = proc.stdout.readline()
        if not line:
            break
        match = url_pattern.search(line)
        if match:
            tunnel_url = match.group(0)
            break

    if not tunnel_url:
        proc.terminate()
        print("Failed to obtain public tunnel URL from cloudflared.", file=sys.stderr)
        sys.exit(1)

    print(f"\n==========================================")
    print(f"Tunnel successfully created: {tunnel_url}")
    print(f"==========================================\n")

    # Set webhook on Telegram
    asyncio.run(cmd_set(tunnel_url))

    print("\nTunnel is ACTIVE and routing updates to your FastAPI server!")
    print("Press Ctrl+C to stop the tunnel (will automatically remove webhook).\n")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nStopping tunnel...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Cleaning up Telegram webhook...")
        asyncio.run(cmd_delete())
        print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="CareBridge Telegram Webhook & Tunnel Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Check current Telegram webhook status")
    
    set_parser = subparsers.add_parser("set", help="Set Telegram webhook URL")
    set_parser.add_argument("url", help="HTTPS base URL or complete webhook URL")

    subparsers.add_parser("delete", help="Delete Telegram webhook (enables polling)")

    tunnel_parser = subparsers.add_parser("tunnel", help="Create cloudflared quick tunnel and set webhook")
    tunnel_parser.add_argument("--port", type=int, default=8000, help="Local FastAPI port (default: 8000)")

    args = parser.parse_args()

    if args.command == "status":
        asyncio.run(cmd_status())
    elif args.command == "set":
        asyncio.run(cmd_set(args.url))
    elif args.command == "delete":
        asyncio.run(cmd_delete())
    elif args.command == "tunnel":
        cmd_tunnel(args.port)


if __name__ == "__main__":
    main()
