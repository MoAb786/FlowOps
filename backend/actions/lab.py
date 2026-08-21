import json
import threading
from pathlib import Path

# ---------------------------------------------------------------------------
# Inventory store — backend/data/inventory.json
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


def _update_lab_inventory(items: list, event_type: str) -> list:
    """
    Atomically update lab component quantities.

    - "issue component"  → decrement (clamped to 0)
    - "return component" → increment

    Returns a list of per-item change records.
    """
    changes = []
    with _inventory_lock:
        inventory = _load_inventory()
        lab_stock = inventory.setdefault("lab", {})

        for item in items:
            name = item["name"]
            qty = item["quantity"]
            before = lab_stock.get(name, 0)

            if event_type == "issue component":
                after = max(0, before - qty)
            else:  # return component
                after = before + qty

            lab_stock[name] = after
            changes.append({"name": name, "quantity": qty, "before": before, "after": after})

        inventory["lab"] = lab_stock
        _save_inventory(inventory)

    return changes


# ---------------------------------------------------------------------------
# Main entry point — called by notion_helper.trigger_domain_action()
# ---------------------------------------------------------------------------
def execute(request: dict) -> dict:
    # ---- validation ----
    if not isinstance(request, dict):
        return {"status": "error", "action": "lab_inventory_updated", "error": "Request must be a dictionary"}

    details = request.get("details")
    if not isinstance(details, dict):
        return {"status": "error", "action": "lab_inventory_updated", "error": "Missing or invalid 'details' dictionary"}

    items = details.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return {"status": "error", "action": "lab_inventory_updated", "error": "Missing or empty 'items' list"}

    event_type = request.get("event_type") or details.get("event_type")
    if event_type not in ["issue component", "return component"]:
        return {"status": "error", "action": "lab_inventory_updated", "error": f"Invalid or missing event_type: {event_type}"}

    request_id = request.get("request_id", "unknown")
    sender_id = request.get("sender_id", "unknown")

    for item in items:
        if not isinstance(item, dict):
            return {"status": "error", "action": "lab_inventory_updated", "error": "Item must be a dictionary"}
        if "name" not in item:
            return {"status": "error", "action": "lab_inventory_updated", "error": "Item missing 'name'"}
        if "quantity" not in item:
            return {"status": "error", "action": "lab_inventory_updated", "error": "Item missing 'quantity'"}
        qty = item["quantity"]
        if not isinstance(qty, int) or qty <= 0:
            return {"status": "error", "action": "lab_inventory_updated", "error": f"Quantity must be a positive integer, got: {qty}"}

    # ---- 1. Persist inventory change ----
    changes = _update_lab_inventory(items, event_type)

    for ch in changes:
        direction = "issued" if event_type == "issue component" else "returned"
        print(
            f"[Lab Inventory] {ch['name']}: {ch['before']} → {ch['after']} "
            f"({ch['quantity']} {direction}) | Request: {request_id}"
        )

    # ---- 2. Log inventory changes ----
    for ch in changes:
        direction = "issued" if event_type == "issue component" else "returned"
        print(
            f"[Lab Inventory] {ch['name']}: {ch['before']} → {ch['after']} "
            f"({ch['quantity']} {direction}) | Request: {request_id}"
        )

    return {
        "status": "success",
        "action": "lab_inventory_updated",
        "items_processed": len(items),
        "inventory_changes": changes
    }
