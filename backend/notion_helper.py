import os
import json
import re
from datetime import datetime
from notion_client import AsyncClient
from telegram_helper import send_telegram, now_ist, build_status_notification

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


# ---------------------------------------------------------------------------
# Human-readable formatting helpers
# ---------------------------------------------------------------------------

def format_details_for_humans(details: dict) -> str:
    """
    Convert a structured details dict into clean bullet-point text for Notion.

    Lab example output:
        • 2x Arduino Uno
        • 1x Breadboard
        Reason: Lab assignment

    Restaurant example output:
        • 2x Burger
        • 1x Coffee
        Table: 3
    """
    lines = []

    items = details.get("items", [])
    for item in items:
        qty = item.get("quantity", "?")
        name = item.get("name", "Unknown item")
        lines.append(f"• {qty}x {name}")

    # Lab fields
    reason = details.get("reason", "")
    if reason:
        lines.append(f"Reason: {reason}")

    # Restaurant fields
    table = details.get("table_number")
    if table:
        lines.append(f"Table: {table}")

    # Fallback for unknown/empty structures
    if not lines:
        # Try to surface any top-level string values
        for key, val in details.items():
            if key not in ("items", "event_type", "needs_human_clarification") and val:
                lines.append(f"{key.replace('_', ' ').capitalize()}: {val}")

    if not lines:
        lines.append("(No structured details available)")

    return "\n".join(lines)


def _build_card_title(request_record: dict) -> str:
    """
    Build a human-readable card title, e.g.:
        Lab Request — Rohan — 2x Arduino Uno
        Restaurant Order — Table 3 — 1x Burger, 2x Coffee
    """
    domain = request_record.get("domain", "unknown").capitalize()
    sender_id = request_record.get("sender_id", "unknown")
    details = request_record.get("details", {})
    items = details.get("items", [])

    if items:
        # Show first item (or first two) as the summary
        item_summaries = [f"{i.get('quantity', '?')}x {i.get('name', '?')}" for i in items[:2]]
        item_summary = ", ".join(item_summaries)
        if len(items) > 2:
            item_summary += f" +{len(items) - 2} more"
    else:
        item_summary = "Unknown items"

    # Distinguish domain phrasing
    if domain.lower() == "restaurant":
        table = details.get("table_number", "?")
        return f"Restaurant Order — Table {table} — {item_summary}"
    else:
        return f"{domain} Request — {sender_id} — {item_summary}"



async def create_pending_card(request_record: dict, processed: bool = False):
    """
    Creates a new card in the Notion Requests database.

    - Card title: human-readable (e.g. "Lab Request — Rohan — 2x Arduino Uno")
    - details property: raw JSON (preserved for webhook/poller machine-reading)
    - Page body: human-readable bullet-point summary (visible when card is opened)
    """
    try:
        card_title = _build_card_title(request_record)
        details_dict = request_record.get("details", {})
        # Keep raw JSON in property for machine reading on approval webhook
        details_json = json.dumps(details_dict)
        # Human-formatted body for the card page content
        details_human = format_details_for_humans(details_dict)

        response = await notion.pages.create(
            parent={"database_id": REQUESTS_DB_ID},
            properties={
                "Name": {"title": [{"text": {"content": card_title}}]},
                "domain": {"select": {"name": request_record.get("domain", "lab")}},
                "sender_id": {"rich_text": [{"text": {"content": request_record.get("sender_id", "")}}]},
                "status": {"select": {"name": request_record["status"]}},
                "risk_level": {"select": {"name": request_record.get("risk_level", "Normal")}},
                "event_type": {"select": {"name": request_record.get("event_type", "issue component")}},
                "details": {"rich_text": [{"text": {"content": details_json}}]},
                "Processed": {"checkbox": processed}
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": details_human}
                            }
                        ]
                    }
                }
            ]
        )
        print(f"[Notion] Created Card successfully: {response.get('id')}")

        # --- Telegram notification for new submissions ---
        status = request_record.get("status", "Pending")
        notifiable_statuses = {"Pending", "Needs Clarification", "Approved", "Denied"}
        if status in notifiable_statuses:
            send_telegram(
                build_status_notification(
                    status=status,
                    request_id=request_record.get("request_id", ""),
                    sender_id=request_record.get("sender_id", "unknown"),
                    details=request_record.get("details", {}),
                )
            )

        return {"status": "success", "notion_id": response.get("id"), "record": request_record}
    except Exception as e:
        print(f"[Notion] Error creating card: {e}")
        return {"status": "error", "error": str(e), "record": request_record}




async def auto_approve_and_log(request_record: dict):
    """
    For low-risk requests, log it and create a card in Notion marked as processed.
    """
    print(f"[System] Auto-approving request {request_record['request_id']}")
    
    # Create the card in the Requests dashboard, marked as processed
    await create_pending_card(request_record, processed=True)

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

        # Build a human-readable log title, e.g.:
        #   "Auto-Approved — issue component — system"
        result_label = log_entry.get("result", "Auto-Approved")
        action_label = log_entry.get("action_taken", "")
        actor_label = log_entry.get("actor", "system")
        log_title = f"{result_label} — {action_label} — {actor_label}"

        response = await notion.pages.create(
            parent={"database_id": RUN_LOG_DB_ID},
            properties={
                "Name": {"title": [{"text": {"content": log_title}}]},
                "action_taken": {"rich_text": [{"text": {"content": action_label}}]},
                "actor": {"rich_text": [{"text": {"content": actor_label}}]},
                "timestamp": {"date": {"start": log_entry.get("timestamp", datetime.utcnow().isoformat())}},
                "result": {"select": {"name": result_label}}
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
    Triggered when a page property updates in Notion via Automation or webhook.

    Notion Automation payloads nest the page under payload["data"].
    Direct API webhooks may put page_id at the top level.
    We try all known shapes so this works regardless of integration method.
    """
    try:
        import json as _json
        print(f"[Webhook] Raw payload received: {_json.dumps(payload)[:500]}")

        # --- Extract page_id from all known Notion payload shapes ---
        # Shape 1: Notion Automation  → payload["data"]["id"]
        # Shape 2: Notion API webhook → payload["entity"]["id"]  or payload["page_id"]
        # Shape 3: Manual / direct    → payload["id"]
        page_id = (
            (payload.get("data") or {}).get("id")
            or (payload.get("entity") or {}).get("id")
            or payload.get("page_id")
            or payload.get("id")
        )

        if not page_id:
            print("[Webhook] No page_id found in webhook payload — check Notion Automation config")
            return
        
        page = await notion.pages.retrieve(page_id=page_id)
        properties = page.get("properties", {})
        
        status = properties.get("status", {}).get("select", {}).get("name")
        processed = properties.get("Processed", {}).get("checkbox", False)
        
        # Handle all actionable statuses that have not yet been processed
        actionable_statuses = {"Approved", "Denied", "Needs Clarification", "Pending"}
        if status in actionable_statuses and not processed:
            # Use page_id as the canonical request identifier (consistent with poller)
            request_id = page_id

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
            
            # Perform domain-level action and write log for terminal statuses
            if status == "Approved":
                await trigger_domain_action(request_record)
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "human approver",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "Manually Approved"
                })
            elif status == "Denied":
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "human approver",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "Denied"
                })
            elif status == "Needs Clarification":
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "human approver",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "Needs Clarification"
                })
            # "Pending" — no domain action, no log; just notify

            # Send Telegram notification for every status change
            send_telegram(
                build_status_notification(
                    status=status,
                    request_id=request_id,
                    sender_id=sender_id,
                    details=details,
                )
            )
            
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

async def get_all_requests():
    """
    Retrieves all requests from the Notion Requests database.
    """
    try:
        response = await notion.request(
            path=f"databases/{REQUESTS_DB_ID}/query",
            method="POST",
            body={
                "sorts": [{"timestamp": "created_time", "direction": "descending"}],
                "page_size": 50
            }
        )
        
        results = []
        for page in response.get("results", []):
            props = page.get("properties", {})
            
            # Extract Request ID
            req_id_list = props.get("Name", {}).get("title", [])
            req_id = req_id_list[0]["text"]["content"] if req_id_list else "unknown"
            
            # Extract Domain
            domain_select = props.get("domain", {}).get("select") or {}
            domain = domain_select.get("name", "")
            
            # Extract Sender
            sender_list = props.get("sender_id", {}).get("rich_text", [])
            sender_id = sender_list[0]["text"]["content"] if sender_list else ""
            
            # Extract Status
            status_select = props.get("status", {}).get("select") or {}
            status = status_select.get("name", "")
            
            # Extract Risk Level
            risk_select = props.get("risk_level", {}).get("select") or {}
            risk_level = risk_select.get("name", "")
            
            # Extract Event Type
            event_select = props.get("event_type", {}).get("select") or {}
            event_type = event_select.get("name", "")
            
            # Extract Details
            details_list = props.get("details", {}).get("rich_text", [])
            details_str = details_list[0]["text"]["content"] if details_list else "{}"
            try:
                details = json.loads(details_str)
            except:
                details = {}
                
            # Extract Created At
            created_at = page.get("created_time", "")
            
            results.append({
                "request_id": req_id,
                "domain": domain,
                "sender_id": sender_id,
                "event_type": event_type,
                "details": details,
                "status": status,
                "risk_level": risk_level,
                "created_at": created_at
            })
            
        return results
    except Exception as e:
        print(f"[Notion] Error fetching requests: {e}")
        return []
