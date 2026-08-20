import os
import json
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "kitchen_queue.log")

def execute(request: dict) -> dict:
    if not isinstance(request, dict):
        return {"status": "error", "action": "restaurant_order_processed", "error": "Request must be a dictionary"}
        
    details = request.get("details")
    if not isinstance(details, dict):
        return {"status": "error", "action": "restaurant_order_processed", "error": "Missing or invalid 'details' dictionary"}
        
    items = details.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return {"status": "error", "action": "restaurant_order_processed", "error": "Missing or empty 'items' list"}
        
    table_number = details.get("table_number")
    if not isinstance(table_number, int) or table_number <= 0:
        return {"status": "error", "action": "restaurant_order_processed", "error": "Missing or invalid 'table_number'"}
        
    event_type = details.get("event_type")
    if event_type not in ["new order", "cancel order"]:
        return {"status": "error", "action": "restaurant_order_processed", "error": f"Invalid or missing event_type: {event_type}"}
        
    request_id = request.get("request_id", "unknown")
    
    # Validate items
    for item in items:
        if not isinstance(item, dict):
            return {"status": "error", "action": "restaurant_order_processed", "error": "Item must be a dictionary"}
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            return {"status": "error", "action": "restaurant_order_processed", "error": "Item missing or empty 'name'"}
        
        qty = item.get("quantity")
        if not isinstance(qty, int) or qty <= 0:
            return {"status": "error", "action": "restaurant_order_processed", "error": f"Quantity must be a positive integer, got: {qty}"}
            
    # File logging
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.utcnow().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "event_type": event_type,
                "table_number": table_number,
                "items": items,
                "request_id": request_id
            }
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        return {"status": "error", "action": "restaurant_order_processed", "error": f"Failed to write log: {str(e)}"}
        
    return {
        "status": "success",
        "action": "restaurant_order_processed",
        "items_processed": len(items)
    }
