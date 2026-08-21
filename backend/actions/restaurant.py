import json
import threading
from pathlib import Path
from telegram_helper import send_telegram, now_ist

# ---------------------------------------------------------------------------
# Shared inventory store — backend/data/inventory.json
# ---------------------------------------------------------------------------
_INVENTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "inventory.json"
_inventory_lock = threading.Lock()


def _load_inventory() -> dict:
    """Load the full inventory JSON from disk."""
    if not _INVENTORY_PATH.exists():
        return {}
    with open(_INVENTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_inventory(data: dict) -> None:
    """Persist the full inventory JSON to disk."""
    _INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_INVENTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _update_restaurant_inventory(items: list, event_type: str) -> list:
    """
    Atomically update restaurant item quantities.

    - "new order"    → decrement available stock (clamped to 0)
    - "cancel order" → restore stock (increment)

    Returns a list of per-item change records.
    """
    changes = []
    with _inventory_lock:
        inventory = _load_inventory()
        restaurant_stock = inventory.setdefault("restaurant", {})

        for item in items:
            name = item["name"]
            qty = item["quantity"]
            before = restaurant_stock.get(name, 0)

            if event_type == "new order":
                after = max(0, before - qty)
            else:  # cancel order
                after = before + qty

            restaurant_stock[name] = after
            changes.append({"name": name, "quantity": qty, "before": before, "after": after})

        inventory["restaurant"] = restaurant_stock
        _save_inventory(inventory)

    return changes


# ---------------------------------------------------------------------------
# Main entry point — called by notion_helper.trigger_domain_action()
# ---------------------------------------------------------------------------
def execute(request: dict) -> dict:
    # ---- validation ----
    if not isinstance(request, dict):
        return {"status": "error", "action": "restaurant_order_processed", "error": "Request must be a dictionary"}

    details = request.get("details")
    if not isinstance(details, dict):
        return {"status": "error", "action": "restaurant_order_processed", "error": "Missing or invalid 'details' dictionary"}

    items = details.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return {"status": "error", "action": "restaurant_order_processed", "error": "Missing or empty 'items' list"}

    # table_number is optional — null or 0 is allowed, displayed as "Unknown"
    table_number = details.get("table_number")
    if table_number is not None and (not isinstance(table_number, int) or table_number <= 0):
        table_number = None  # treat invalid (e.g. 0) the same as missing
    table_display = str(table_number) if table_number else "Unknown"

    event_type = request.get("event_type") or details.get("event_type")
    if event_type not in ["new order", "cancel order"]:
        return {"status": "error", "action": "restaurant_order_processed", "error": f"Invalid or missing event_type: {event_type}"}

    request_id = request.get("request_id", "unknown")
    sender_id = request.get("sender_id", "unknown")

    for item in items:
        if not isinstance(item, dict):
            return {"status": "error", "action": "restaurant_order_processed", "error": "Item must be a dictionary"}
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            return {"status": "error", "action": "restaurant_order_processed", "error": "Item missing or empty 'name'"}
        qty = item.get("quantity")
        if not isinstance(qty, int) or qty <= 0:
            return {"status": "error", "action": "restaurant_order_processed", "error": f"Quantity must be a positive integer, got: {qty}"}

    # ---- 1. Persist inventory change ----
    changes = _update_restaurant_inventory(items, event_type)

    for ch in changes:
        direction = "ordered" if event_type == "new order" else "cancelled"
        print(
            f"[Restaurant Inventory] {ch['name']}: {ch['before']} → {ch['after']} "
            f"({ch['quantity']} {direction}) | Table {table_display} | Request: {request_id}"
        )

    # ---- 2. Send Telegram notification ----
    item_lines = "\n".join(f"  \u2022 {ch['quantity']}x {ch['name']}" for ch in changes)
    short_id = str(request_id)[:8].upper()
    action_label = "New Order Placed" if event_type == "new order" else "Order Cancelled"

    tg_message = (
        f"\U0001f37d\ufe0f <b>Restaurant Order {action_label}</b>\n"
        f"\U0001f516 Request ID: {short_id}\n"
        f"\U0001f4cb Table: {table_display} | Placed by: {sender_id}\n"
        f"\U0001f6d2 Items:\n{item_lines}\n"
        f"\U0001f550 {now_ist()}"
    )
    send_telegram(tg_message)

    return {
        "status": "success",
        "action": "restaurant_order_processed",
        "items_processed": len(items),
        "inventory_changes": changes
    }

