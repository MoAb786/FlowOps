import os
import json
from datetime import datetime

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
            
    # Console logging
    for item in items:
        print(f"[Lab Action] {event_type} - {item['quantity']}x {item['name']} (Request: {request_id})")
        
    return {
        "status": "success",
        "action": "lab_inventory_updated",
        "items_processed": len(items)
    }
