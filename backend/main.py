from dotenv import load_dotenv
load_dotenv()

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from core import handle_new_request
from notion_helper import process_notion_webhook, get_all_requests
from poller import poll_notion_updates
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background poller
    async def poller_loop():
        print("[System] Background Notion Poller started.")
        while True:
            try:
                await poll_notion_updates()
            except Exception as e:
                print(f"[Poller Loop Error] {e}")
            await asyncio.sleep(20) # Poll every 20 seconds
            
    task = asyncio.create_task(poller_loop())
    yield
    # Shutdown
    task.cancel()

app = FastAPI(title="FlowOps Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/requests")
async def get_requests():
    return await get_all_requests()

@app.get("/inventory")
async def get_inventory():
    from pathlib import Path
    import json
    inventory_path = Path(__file__).resolve().parent / "data" / "inventory.json"
    if not inventory_path.exists():
        return {}
    with open(inventory_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/requests")
async def submit_request(request: Request):
    data = await request.json()
    raw_text = data.get("text")
    domain = data.get("domain", "lab")
    sender_id = data.get("sender_id", "unknown")
    
    result = await handle_new_request(raw_text, domain, sender_id)
    return result

@app.post("/webhooks/notion")
async def notion_webhook(request: Request):
    payload = await request.json()
    await process_notion_webhook(payload)
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
