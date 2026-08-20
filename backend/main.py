from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from core import handle_new_request
from notion_helper import process_notion_webhook
import uvicorn

app = FastAPI(title="FlowOps Engine")

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
