import os
import json
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "lab_inventory.log")

def execute(request: dict) -> dict:
    if not isinstance(request, dict):
        return {"status": "error", "action": "lab_inventory_updated", "error": "Request must be a dictionary"}
        
    details = request.get("details")
    if not isinstance(details, dict):
        return {"status": "error", "action": "lab_inventory_updated", "error": "Missing or invalid 'details' dictionary"}
        
    items = details.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return {"status": "error", "action": "lab_inventory_updated", "error": "Missing or empty 'items' list"}
        
    event_type = details.get("event_type")
    if event_type not in ["issue component", "return component"]:
        return {"status": "error", "action": "lab_inventory_updated", "error": f"Invalid or missing event_type: {event_type}"}
        
    request_id = request.get("request_id", "unknown")
    
    # Validate items
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
            
    # File logging
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            for item in items:
                timestamp = datetime.utcnow().isoformat()
                log_entry = {
                    "timestamp": timestamp,
                    "event_type": event_type,
                    "item_name": item["name"],
                    "quantity": item["quantity"],
                    "request_id": request_id
                }
                f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        return {"status": "error", "action": "lab_inventory_updated", "error": f"Failed to write log: {str(e)}"}
        
    return {
        "status": "success",
        "action": "lab_inventory_updated",
        "items_processed": len(items)
    }
