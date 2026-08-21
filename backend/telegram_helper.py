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


def format_item_lines(details: dict) -> str:
    """
    Format the items list from a details dict into Telegram-ready bullet lines.

    Returns something like:
        • 1x Arduino Uno
        • 2x LED
    or a fallback string if no items are present.
    """
    items = details.get("items", []) if isinstance(details, dict) else []
    if items:
        return "\n".join(
            f"  \u2022 {i.get('quantity', '?')}x {i.get('name', '?')}"
            for i in items
        )
    return "  (see Notion for details)"


def build_status_notification(status: str, request_id: str, sender_id: str, details: dict) -> str:
    """
    Build a fully-formatted Telegram notification string for any request status.

    Statuses handled: Pending, Approved, Denied, Needs Clarification
    """
    short_id = str(request_id)[:8].upper()
    item_lines = format_item_lines(details)
    timestamp = now_ist()

    if status == "Approved":
        header = "\u2705 <b>Lab Request Approved</b>"
    elif status == "Denied":
        header = "\u274c <b>Request Denied</b>"
    elif status == "Needs Clarification":
        header = "\u2753 <b>Request Needs Clarification</b>"
    else:  # Pending or any other
        header = "\u23f3 <b>Request Pending</b>"

    return (
        f"{header}\n"
        f"\U0001f516 Request ID: {short_id}\n"
        f"\U0001f464 Issued to: {sender_id}\n"
        f"\U0001f4e6 Items:\n{item_lines}\n"
        f"\U0001f550 {timestamp}"
    )


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
