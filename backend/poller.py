import json
from datetime import datetime
from notion_helper import notion, REQUESTS_DB_ID, trigger_domain_action, write_run_log, update_card_status_and_process

async def poll_notion_updates():
    """
    Queries Notion Requests DB for unprocessed Approved or Denied cards.
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
                                {"property": "status", "select": {"equals": "Denied"}}
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
            return
            
        print(f"[Poller] Found {len(results)} unprocessed approved/denied card(s)")
        
        for page in results:
            page_id = page["id"]
            properties = page.get("properties", {})
            
            status_obj = properties.get("status", {}).get("select")
            status = status_obj.get("name") if status_obj else None
            if not status:
                continue
            
            # Extract request details
            request_id_list = properties.get("Name", {}).get("title", [])
            if not request_id_list:
                request_id_list = properties.get("request_id", {}).get("title", [])
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
            
            # Process based on decision
            if status == "Approved":
                await trigger_domain_action(request_record)
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "system poller",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "Manually Approved"
                })
            else:
                await write_run_log({
                    "request_id": request_id,
                    "action_taken": event_type,
                    "actor": "system poller",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": "Denied"
                })
                
            # Mark the card as Processed in Notion
            await update_card_status_and_process(page_id, status, processed=True)
            
    except Exception as e:
        print(f"[Poller] Error in poller loop: {e}")
