import os
import json
from datetime import datetime

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
            
    # Console logging
    item_str = ", ".join([f"{i.get('quantity')}x {i.get('name')}" for i in items])
    print(f"[Restaurant Action] {event_type} - Table {table_number} - {item_str} (Request: {request_id})")
        
    return {
        "status": "success",
        "action": "restaurant_order_processed",
        "items_processed": len(items)
    }
