import os
import json
from datetime import datetime
from notion_client import AsyncClient

# Initialize Notion Client
notion = AsyncClient(auth=os.environ.get("NOTION_API_KEY"))
# You'll also need the Database IDs to perform operations.
REQUESTS_DB_ID = os.environ.get("NOTION_REQUESTS_DB_ID")

async def create_pending_card(request_record: dict):
    """
    Creates a new card in the Notion Pending Requests database.
    """
    try:
        # Create a new page in the Notion DB
        response = await notion.pages.create(
            parent={"database_id": REQUESTS_DB_ID},
            properties={
                "request_id": {"title": [{"text": {"content": request_record["request_id"]}}]},
                "domain": {"select": {"name": request_record.get("domain", "lab")}},
                "sender_id": {"rich_text": [{"text": {"content": request_record.get("sender_id", "")}}]},
                "status": {"select": {"name": request_record["status"]}},
                "risk_level": {"select": {"name": request_record.get("risk_level", "Normal")}},
                "event_type": {"select": {"name": request_record.get("event_type", "issue component")}},
                "details": {"rich_text": [{"text": {"content": json.dumps(request_record.get("details", {}))}}]}
            }
        )
        print(f"[Notion] Created Pending Card successfully: {response.get('id')}")
        return {"status": "success", "notion_id": response.get("id"), "record": request_record}
    except Exception as e:
        print(f"[Notion] Error creating pending card: {e}")
        return {"status": "error", "error": str(e), "record": request_record}

async def auto_approve_and_log(request_record: dict):
    """
    For low-risk requests, skip Notion pending queue, just log it.
    """
    print(f"[System] Auto-approving request {request_record['request_id']}")
    await write_run_log({
        "request_id": request_record["request_id"],
        "action_taken": request_record["event_type"],
        "actor": "system",
        "timestamp": datetime.utcnow().isoformat(),
        "result": "Auto-Approved"
    })
    
    # Trigger the real-world action based on domain
    await trigger_domain_action(request_record)
    
    return {"status": "success", "record": request_record}

async def write_run_log(log_entry: dict):
    """
    Writes an entry to the Notion Run Log DB.
    """
    print(f"[Notion] Write Run Log: {log_entry}")

async def process_notion_webhook(payload: dict):
    """
    Triggered when a page property updates in Notion.
    """
    # 1. Fetch updated status from Notion
    # 2. If approved, trigger action and log
    print(f"[Webhook] Received update: {payload}")

async def trigger_domain_action(request_record: dict):
    domain = request_record.get("domain")
    if domain == "lab":
        from actions.lab import execute
        execute(request_record)
    elif domain == "restaurant":
        from actions.restaurant import execute
        execute(request_record)
