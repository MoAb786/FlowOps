# FlowOps — Fix Diff Summary

> **All 3 gaps from `analysis.md` addressed.** Files ready to review and commit.

---

## Fix 1 — Real External Side Effects (`lab.py` & `restaurant.py`)

### New file: `backend/data/inventory.json`
Seeded with default stock quantities for lab components and restaurant menu items. Acts as the persistent real-world state store.

```json
{
  "lab":        { "Arduino Uno": 20, "Breadboard": 30, "LED": 200, ... },
  "restaurant": { "Burger": 50, "Pizza": 30, "Coffee": 100, ... }
}
```

---

### `backend/actions/lab.py`

| Before | After |
|---|---|
| `import os, json` only | Added `threading`, `urllib.request`, `urllib.error`, `pathlib.Path` |
| `print(f"[Lab Action] ...")` only — no real state change | **Atomically** reads/updates `inventory.json` with `threading.Lock()` |
| No notifications | Sends Telegram HTML message via Bot API on every approval |
| Returns `items_processed` only | Returns `items_processed` + `inventory_changes` list |

**Key additions:**

```python
# Thread-safe inventory update
def _update_lab_inventory(items, event_type) -> list[dict]:
    with _inventory_lock:
        inventory = _load_inventory()
        # issue component → decrement (clamped to 0)
        # return component → increment
        _save_inventory(inventory)
    return changes   # [{name, quantity, before, after}, ...]

# Telegram notification (HTML, no third-party deps)
def _send_telegram_notification(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Reads TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID from env
    # Skips gracefully if either is missing
```

**Telegram message format:**
```
✅ Lab Request Approved
🔖 Request ID: A3F1B2C9
👤 Issued to: rohan@college.edu
📦 Items:
  • 2x Arduino Uno
  • 1x Breadboard
📝 Reason: Lab assignment
🕐 2026-08-21 13:05 UTC
```

---

### `backend/actions/restaurant.py`

Same pattern as `lab.py`:
- `_update_restaurant_inventory()` — decrement on `"new order"`, increment on `"cancel order"`
- `_send_telegram_notification()` — sends formatted Telegram message with table number and items
- Returns `inventory_changes` alongside existing fields

---

## Fix 2 — Human-Readable Notion Cards (`notion_helper.py`)

### New functions added

```python
def format_details_for_humans(details: dict) -> str:
    """
    • 2x Arduino Uno
    • 1x Breadboard
    Reason: Lab assignment
    """

def _build_card_title(request_record: dict) -> str:
    # "Lab Request — Rohan — 2x Arduino Uno"
    # "Restaurant Order — Table 3 — 1x Burger, 2x Coffee"
```

### `create_pending_card()` changes

| Property | Before | After |
|---|---|---|
| `Name` | raw UUID (`request_id`) | Human title: `"Lab Request — Rohan — 2x Arduino Uno"` |
| `details` property | `json.dumps(details)` | Raw JSON preserved (**for machine reading on webhook**) |
| Page body content | *(nothing)* | Human bullet-point text rendered as `paragraph` block inside the card |

> **Design decision:** Raw JSON stays in the `details` *property* so the webhook/poller can reconstruct structured data on approval. The human-readable summary is written as the page's *body content* (visible when you open the card in Notion).

### `write_run_log()` changes

| Before | After |
|---|---|
| `Name` = raw UUID | `Name` = `"Auto-Approved — issue component — system"` |

---

## Fix 3 — Read-Only Dashboard (`dashboard.astro`)

| Element | Before | After |
|---|---|---|
| Page `<title>` | `"Dashboard - FlowOps"` | `"My Requests — FlowOps"` |
| `<h1>` | `"Dashboard"` | `"My Requests"` |
| Subtitle | `"Track and manage all your requests in one place."` | `"Track the status of requests you have submitted."` |
| Header button | `"+ New Request"` (ambiguous) | `"+ Submit New Request"` (submission only) |
| Info banner | *(absent)* | Blue info box: **"Tracking view only. All approvals are handled exclusively inside Notion by authorized operators."** |
| Approve/reject controls | *(none were present — confirmed)* | *(none — dashboard was already read-only; framing now makes it explicit)* |
| HTML comments | *(none)* | `<!-- IMPORTANT: READ-ONLY ... All management stays in Notion -->` added in source |

---

## New env variables

Added to both `.env` and `.env.example`:

```env
TELEGRAM_BOT_TOKEN=<your bot token from BotFather>
TELEGRAM_CHAT_ID=<your chat/group ID>
```

> **Get your `TELEGRAM_CHAT_ID`:** Message your bot (`@FlowOpsRequestBot`), then visit:
> `https://api.telegram.org/bot<TOKEN>/getUpdates`
> and copy the `"id"` from the `"chat"` object.

---

## Verification Checklist

- [ ] Open `backend/data/inventory.json` before and after submitting a lab request → numbers change
- [ ] Trigger an approval in Notion → Telegram message arrives with readable bullet-point format
- [ ] Open a Notion request card → page body shows `• 2x Arduino Uno` style text, title reads `"Lab Request — …"`
- [ ] Open Notion run log → entry title reads `"Auto-Approved — issue component — system"` not a UUID
- [ ] Open `dashboard.astro` in browser → blue info banner visible, no approve/reject buttons
- [ ] Set `TELEGRAM_CHAT_ID` in `.env` (see above for how to get it)
