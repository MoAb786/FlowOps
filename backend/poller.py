import json
from datetime import datetime
from notion_helper import notion, REQUESTS_DB_ID, trigger_domain_action, write_run_log, update_card_status_and_process
from telegram_helper import send_telegram, build_status_notification

async def poll_notion_updates():
    """
    Queries Notion Requests DB for unprocessed cards whose status has changed
    to Approved, Denied, or Needs Clarification, then sends Telegram notifications
    and performs any required domain actions.
    """
    if not REQUESTS_DB_ID:
        print("[Poller] Warning: NOTION_REQUESTS_DB_ID is not configured in .env")
        return
        
    try:
        response = await notion.request(
            path=f"databases/{REQUESTS_DB_ID}/query",
            method="POST",
            body={
                "filter": {
                    "and": [
                        {
                            "or": [
                                {"property": "status", "select": {"equals": "Approved"}},
                                {"property": "status", "select": {"equals": "Denied"}},
                                {"property": "status", "select": {"equals": "Needs Clarification"}},
                                {"property": "status", "select": {"equals": "Auto-Approved"}}
                            ]
                        },
                        {
                            "property": "Processed",
                            "checkbox": {"equals": False}
                        }
                    ]
                }
            }
        )
        
        results = response.get("results", [])
        if not results:
            print("[Poller] ✓ Checked Notion — no unprocessed status changes found.")
            return
            
        print(f"[Poller] Found {len(results)} unprocessed card(s) with updated status")
        
        for page in results:
            page_id = page["id"]
            properties = page.get("properties", {})
            
            status_obj = properties.get("status", {}).get("select")
            status = status_obj.get("name") if status_obj else None
            if not status:
                continue
            
            # Use page_id as the request_id — the Name property holds the
            # human-readable title (e.g. "Lab Request — user_123 — 1x Arduino Uno"),
            # not the original UUID.
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
            
            # Perform domain-level actions and write audit log
            if status in ["Approved", "Auto-Approved"]:
                await trigger_domain_action(request_record)
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "system poller",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": status
                })
            elif status == "Denied":
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "system poller",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "Denied"
                })
            elif status == "Needs Clarification":
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "system poller",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "Needs Clarification"
                })

            # Send Telegram notification with full request details for every status
            send_telegram(
                build_status_notification(
                    status=status,
                    request_id=request_id,
                    sender_id=sender_id,
                    details=details,
                )
            )
                
            # Mark the card as Processed in Notion so it won't be re-notified
            await update_card_status_and_process(page_id, status, processed=True)
            
    except Exception as e:
        print(f"[Poller] Error in poller loop: {e}")

