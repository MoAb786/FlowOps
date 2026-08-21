from parser import parse_request
from router import route_request
from notion_helper import create_pending_card, auto_approve_and_log
import uuid
from datetime import datetime

async def handle_new_request(raw_text: str, domain: str, sender_id: str):
    # 1. PARSE
    parsed_data = parse_request(raw_text, domain)
    print(f"[Core] Parsed data: {parsed_data}")

    if parsed_data.get("needs_human_clarification"):
        print(f"[Core] needs_human_clarification=True → creating 'Needs Clarification' card")
        # Handle ambiguous input
        return await create_pending_card({
            "request_id": str(uuid.uuid4()),
            "domain": domain,
            "sender_id": sender_id,
            "status": "Needs Clarification",
            "details": parsed_data,
            "created_at": datetime.utcnow().isoformat()
        })

    # 2. ROUTE
    risk_level, mapped_approver = route_request(parsed_data, domain)
    print(f"[Core] risk_level={risk_level!r}, approver={mapped_approver!r}")

    request_record = {
        "request_id": str(uuid.uuid4()),
        "domain": domain,
        "sender_id": sender_id,
        "receiver_id": mapped_approver,
        "event_type": parsed_data.get("event_type", "issue"),
        "details": parsed_data,
        "status": "Pending",
        "risk_level": risk_level,
        "created_at": datetime.utcnow().isoformat()
    }

    # 3. APPROVAL OR EXECUTION
    if risk_level == "NORMAL":
        print(f"[Core] NORMAL risk → auto-approving")
        request_record["status"] = "Auto-Approved"
        return await auto_approve_and_log(request_record)
    else:
        print(f"[Core] {risk_level} risk → creating pending card for human review")
        return await create_pending_card(request_record)
