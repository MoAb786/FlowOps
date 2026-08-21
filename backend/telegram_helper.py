import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# IST = UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> str:
    """Return current time as a formatted IST string."""
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def send_telegram(message: str) -> None:
    """
    Send a message to the configured Telegram chat via the Bot API.

    Requires env vars:
      TELEGRAM_BOT_TOKEN  — bot token from BotFather
      TELEGRAM_CHAT_ID    — chat/channel/group ID to deliver to
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print("[Telegram] Skipping notification — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[Telegram] Notification sent. Status: {resp.status}")
    except urllib.error.URLError as e:
        print(f"[Telegram] Notification failed: {e.reason}")
