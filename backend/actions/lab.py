def execute(request: dict) -> dict:
    print(f"[Action: Lab] Processing inventory update for request: {request['request_id']}")
    items = request.get("details", {}).get("items", [])
    for item in items:
        print(f"  - Issuing {item['quantity']} of {item['name']}")
    return {"status": "success", "action": "lab_inventory_updated"}
