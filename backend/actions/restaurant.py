def execute(request: dict) -> dict:
    print(f"[Action: Restaurant] Notifying kitchen for order: {request['request_id']}")
    items = request.get("details", {}).get("items", [])
    for item in items:
        print(f"  - Cooking {item['quantity']} of {item['name']}")
    return {"status": "success", "action": "kitchen_notified"}
