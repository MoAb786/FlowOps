def route_request(parsed_data: dict, domain: str):
    """
    Determines risk level and mapped approver based on the extracted data.
    """
    risk_level = "High"
    approver = "operator"

    if domain == "lab":
        items = parsed_data.get("items", [])
        total_quantity = sum([item.get("quantity", 0) for item in items])
        
        # Adaptive Approval Rule:
        if total_quantity <= 2:
            risk_level = "Normal"
            
    elif domain == "restaurant":
        risk_level = "Normal" # Restaurant orders are lower risk usually
        approver = "kitchen"

    return risk_level, approver
