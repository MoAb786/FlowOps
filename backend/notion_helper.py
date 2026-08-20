import os
import json
import re
from datetime import datetime
from notion_client import AsyncClient

def clean_notion_id(raw_id: str) -> str:
    """
    Cleans a Notion database or page ID if a full URL or formatted UUID was provided.
    """
    if not raw_id:
        return ""
    raw_id = raw_id.strip()
    if "/" in raw_id:
        raw_id = raw_id.split("/")[-1]
    if "?" in raw_id:
        raw_id = raw_id.split("?")[0]
    return raw_id.replace("-", "")

# Initialize Notion Client with stable API version for database queries
notion = AsyncClient(
    auth=os.environ.get("NOTION_API_KEY"),
    notion_version="2022-06-28"
)
REQUESTS_DB_ID = clean_notion_id(os.environ.get("NOTION_REQUESTS_DB_ID", ""))
RUN_LOG_DB_ID = clean_notion_id(os.environ.get("NOTION_RUN_LOG_DB_ID", ""))

async def create_pending_card(request_record: dict):
    """
    Creates a new card in the Notion Pending Requests database.
    """
    try:
        response = await notion.pages.create(
            parent={"database_id": REQUESTS_DB_ID},
            properties={
                "Name": {"title": [{"text": {"content": request_record["request_id"]}}]},
                "domain": {"select": {"name": request_record.get("domain", "lab")}},
                "sender_id": {"rich_text": [{"text": {"content": request_record.get("sender_id", "")}}]},
                "status": {"select": {"name": request_record["status"]}},
                "risk_level": {"select": {"name": request_record.get("risk_level", "Normal")}},
                "event_type": {"select": {"name": request_record.get("event_type", "issue component")}},
                "details": {"rich_text": [{"text": {"content": json.dumps(request_record.get("details", {}))}}]},
                "Processed": {"checkbox": False}
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
    await trigger_domain_action(request_record)
    return {"status": "success", "record": request_record}

async def write_run_log(log_entry: dict):
    """
    Writes an entry to the Notion Run Log DB.
    """
    try:
        if not RUN_LOG_DB_ID:
            print("[Notion] Warning: NOTION_RUN_LOG_DB_ID is not configured in .env")
            return {"status": "skipped"}
            
        response = await notion.pages.create(
            parent={"database_id": RUN_LOG_DB_ID},
            properties={
                "Name": {"title": [{"text": {"content": log_entry["request_id"]}}]},
                "action_taken": {"rich_text": [{"text": {"content": log_entry.get("action_taken", "")}}]},
                "actor": {"rich_text": [{"text": {"content": log_entry.get("actor", "system")}}]},
                "timestamp": {"date": {"start": log_entry.get("timestamp", datetime.utcnow().isoformat())}},
                "result": {"select": {"name": log_entry.get("result", "Auto-Approved")}}
            }
        )
        print(f"[Notion] Logged run successfully: {response.get('id')}")
        return {"status": "success", "log_id": response.get("id")}
    except Exception as e:
        print(f"[Notion] Error writing run log: {e}")
        return {"status": "error", "error": str(e)}

async def update_card_status_and_process(page_id: str, status: str, processed: bool = True):
    """
    Updates the status and Processed checkbox of a card in the Requests DB.
    """
    try:
        await notion.pages.update(
            page_id=page_id,
            properties={
                "status": {"select": {"name": status}},
                "Processed": {"checkbox": processed}
            }
        )
        print(f"[Notion] Updated card {page_id} status to {status} and Processed={processed}")
        return {"status": "success"}
    except Exception as e:
        print(f"[Notion] Error updating card {page_id}: {e}")
        return {"status": "error", "error": str(e)}

async def process_notion_webhook(payload: dict):
    """
    Triggered when a page property updates in Notion.
    """
    try:
        page_id = payload.get("page_id") or payload.get("id")
        if not page_id:
            print("[Webhook] No page_id found in webhook payload")
            return
        
        page = await notion.pages.retrieve(page_id=page_id)
        properties = page.get("properties", {})
        
        status = properties.get("status", {}).get("select", {}).get("name")
        processed = properties.get("Processed", {}).get("checkbox", False)
        
        if status in ["Approved", "Denied"] and not processed:
            request_id_list = properties.get("Name", {}).get("title", [])
            request_id = request_id_list[0]["text"]["content"] if request_id_list else "unknown"
            domain = properties.get("domain", {}).get("select", {}).get("name", "lab")
            event_type = properties.get("event_type", {}).get("select", {}).get("name", "issue component")
            
            details_list = properties.get("details", {}).get("rich_text", [])
            details_str = details_list[0]["text"]["content"] if details_list else "{}"
            try:
                details = json.loads(details_str)
            except Exception:
                details = {}
            
            sender_id_list = properties.get("sender_id", {}).get("rich_text", [])
            sender_id = sender_id_list[0]["text"]["content"] if sender_id_list else "unknown"
            
            request_record = {
                "request_id": request_id,
                "domain": domain,
                "event_type": event_type,
                "details": details,
                "sender_id": sender_id,
                "status": status
            }
            
            if status == "Approved":
                await trigger_domain_action(request_record)
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "human approver",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "Manually Approved"
                })
            else:
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "human approver",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "Denied"
                })
            
            await update_card_status_and_process(page_id, status, processed=True)
            
    except Exception as e:
        print(f"[Webhook] Error processing Notion webhook: {e}")

async def trigger_domain_action(request_record: dict):
    domain = request_record.get("domain")
    if domain == "lab":
        from actions.lab import execute
        execute(request_record)
    elif domain == "restaurant":
        from actions.restaurant import execute
        execute(request_record)
