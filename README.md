# ⚡ FlowOps — Autonomous Operations Engine with Notion Control & Real-Time Dispatch

> **Automating repetitive operational workflows with Notion as the Human-in-the-Loop interface and external real-world action execution.**

---

## 📌 1. Overview & Problem Statement

Every college lab, workshop, club, and small organization faces repetitive manual bottlenecks:
- Requests submitted in messy natural language across chat groups.
- Manual tracking in spreadsheets where items get lost or delayed.
- Bottlenecks in inventory and approvals without clear audit trails.

**FlowOps** solves this by turning **Notion into an operational command center** driven by an autonomous backend engine:
1. **Inbound Trigger:** Users submit requests in natural language (via web UI or API).
2. **AI Parsing & Multi-Factor Risk Assessment:** Deep extraction of quantities, components, and context; evaluates risk (*Normal*, *Medium*, *High*).
3. **Notion as the Control Panel:**
   - **Normal Risk:** Auto-approved instantly, logged, and executed.
   - **Medium / High Risk / Ambiguous:** Pauses for human review inside Notion (*Pending* / *Needs Clarification*).
4. **Autonomous Polling & Webhook Engine:** Listens for human decisions made directly in Notion (*Approved*, *Denied*, *Needs Clarification*).
5. **Real-World Action & Audit Proof:** Updates real-world domain states (e.g. lab hardware inventory), writes an immutable row in the Notion **Run Log**, and dispatches structured **Telegram alerts**.

---

## 🏗️ 2. System Architecture

```mermaid
flowchart TD
    User([👤 User / Requester]) -->|Natural Language Request| WebUI[🌐 Astro Web Frontend]
    WebUI -->|POST /requests| Engine[⚙️ FlowOps Engine FastAPI]
    
    subgraph "AI Intelligence Layer"
        Engine --> LLMParser[🧠 AI Parser Groq + Gemini Fallback]
        LLMParser --> RiskEngine[⚖️ Contextual Risk Assessment]
    end
    
    subgraph "Notion Operations Hub"
        RiskEngine -->|Normal Risk| AutoApprove[⚡ Auto-Approve & Process]
        RiskEngine -->|Medium / High Risk| NotionReq[📋 Notion Requests DB - Pending]
        RiskEngine -->|Unclear Info| NotionClarify[❓ Notion Requests DB - Needs Clarification]
        HumanApprover([👨‍💼 Operator in Notion]) -->|Approves / Denies / Overrides| NotionReq
    end
    
    subgraph "Execution & Poller Engine"
        NotionReq -->|Async Poller / Webhook| Poller[🔄 Background Poller Loop]
        AutoApprove --> DomainAction[📦 Domain Action: Lab Inventory Update]
        Poller -->|On Human Status Update| DomainAction
        DomainAction --> RunLog[(📗 Notion Run Log DB)]
        DomainAction --> TG[📱 Telegram Bot Dispatcher]
    end
```

---

## 🚀 3. Key Features

- **🧠 Contextual AI Parsing & Fallbacks:** Uses Groq (primary) with seamless Gemini fallback to turn free-text prompts into structured JSON without hardcoded dictionaries.
- **⚖️ Dynamic Multi-Factor Risk Routing:** Evaluates safety, quantity relative to item value, and operational impact.
- **📋 Notion as the True Control Panel:** Operators review, approve, deny, or ask for clarification directly inside Notion.
- **🔄 Zero-Paid-Tier Dependency:** Functions autonomously via an asynchronous cron poller loop (10s interval) or direct HTTP webhooks.
- **📱 Rich Telegram Dispatch:** Real-time formatted notifications with dynamic component itemization, status headers, request IDs, and IST timestamps.
- **📗 Verifiable Run Log Audit Trail:** Writes every single executed action to an immutable Notion Run Log database with timestamps and actor attribution.

---

## 📱 4. Telegram Notification Schema

All status transitions trigger clear, structured Telegram messages with dynamic item bullets:

| Approved Request | Request Needs Clarification | Denied Request |
| :--- | :--- | :--- |
| <pre>✅ <b>Lab Request Approved</b><br/>🔖 Request ID: E2A199FB<br/>👤 Issued to: user_123<br/>📦 Items:<br/>  • 1x Arduino Uno<br/>  • 2x LED<br/>🕐 2026-08-21 20:21 IST</pre> | <pre>❓ <b>Request Needs Clarification</b><br/>🔖 Request ID: E2A199FB<br/>👤 Issued to: user_123<br/>📦 Items:<br/>  • 1x Arduino Uno<br/>  • 2x LED<br/>🕐 2026-08-21 20:21 IST</pre> | <pre>❌ <b>Request Denied</b><br/>🔖 Request ID: E2A199FB<br/>👤 Issued to: user_123<br/>📦 Items:<br/>  • 1x Arduino Uno<br/>  • 2x LED<br/>🕐 2026-08-21 20:21 IST</pre> |

---

## 📂 5. Project Structure

```
FlowOps/
├── backend/
│   ├── actions/
│   │   ├── lab.py              # Inventory decrement/increment & state mutation
│   │   └── restaurant.py       # Restaurant order domain handler
│   ├── data/
│   │   └── inventory.json      # Atomic persistent inventory store
│   ├── ai_client.py            # Groq + Gemini LLM client with automatic failover
│   ├── core.py                 # Request pipeline controller (Parse -> Route -> Act)
│   ├── main.py                 # FastAPI application with background lifespan poller
│   ├── notion_helper.py        # Notion API integration, card creator, run logger
│   ├── parser.py               # Natural language extraction prompt & parser
│   ├── poller.py               # Autonomous Notion database poller for status changes
│   ├── router.py               # Multi-factor risk assessment & approver routing
│   ├── telegram_helper.py      # Rich Telegram Bot API messaging client
│   ├── requirements.txt        # Python backend dependencies
│   └── .env.example            # Backend environment variables template
│
├── frontend/
│   ├── src/
│   │   ├── components/         # Astro & UI components (RequestForm.astro)
│   │   ├── pages/              # index.astro, dashboard.astro, inventory.astro
│   │   └── styles/             # Global CSS styling
│   ├── astro.config.mjs        # Astro configuration
│   └── package.json            # Node.js dependencies
│
└── README.md                   # Project documentation & setup guide
```

---

## 🛠️ 6. Setup & Installation

### Prerequisites
- **Python:** 3.10 or higher
- **Node.js:** 18.x or higher
- **Notion Integration Token & Database IDs**
- **Telegram Bot Token & Chat ID**

---

### Step 1: Backend Configuration

1. Navigate to the backend directory and set up a virtual environment:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure your environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your API credentials:
   ```ini
   # LLM Keys
   GROQ_API_KEY=gsk_...
   GEMINI_API_KEY=AI...

   # Notion Integration
   NOTION_API_KEY=secret_...
   NOTION_REQUESTS_DB_ID=your_requests_database_id
   NOTION_RUN_LOG_DB_ID=your_run_log_database_id

   # Telegram Bot
   TELEGRAM_BOT_TOKEN=123456789:ABC...
   TELEGRAM_CHAT_ID=your_chat_id
   ```

3. Start the backend server:
   ```bash
   python main.py
   # Or: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### Step 2: Frontend Setup

1. In a new terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Open [http://localhost:4321](http://localhost:4321) in your browser.

---

### Step 3: Notion Database Schema

#### 1. Requests Database (`NOTION_REQUESTS_DB_ID`)
- `Name` (*Title*): Human-readable summary (e.g. `Lab Request — user_123 — 2x Arduino Uno`)
- `status` (*Select*): `Pending`, `Approved`, `Denied`, `Needs Clarification`, `Auto-Approved`
- `domain` (*Select*): `lab`, `restaurant`
- `sender_id` (*Rich Text*): Requester user ID
- `risk_level` (*Select*): `NORMAL`, `MEDIUM`, `HIGH`
- `event_type` (*Select*): `issue component`, `return component`
- `details` (*Rich Text*): Structured JSON representation
- `Processed` (*Checkbox*): Checkbox tracked by the autonomous poller

#### 2. Run Log Database (`NOTION_RUN_LOG_DB_ID`)
- `Name` (*Title*): Summary of execution (e.g. `Manually Approved — issue component — human approver`)
- `action_taken` (*Rich Text*): Action executed
- `actor` (*Rich Text*): `system`, `human approver`, or `system poller`
- `timestamp` (*Date*): Execution ISO timestamp
- `result` (*Select*): `Auto-Approved`, `Manually Approved`, `Denied`, `Needs Clarification`

---

## 📡 7. API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/requests` | Submit a natural language request payload (`text`, `domain`, `sender_id`) |
| `GET` | `/requests` | Fetch all historical requests directly from Notion |
| `GET` | `/inventory` | Fetch real-time available stock levels |
| `GET` | `/poll/trigger` | Manually fire an instant Notion database poll cycle |
| `POST` | `/webhooks/notion` | Receive inbound Notion automation webhook payloads |
| `GET` | `/health` | Health check endpoint |

---

## 🧪 8. End-to-End Verification Flow

1. **Submit Request:**
   Submit `"I need 1 Arduino Uno and 2 LEDs for my IoT lab assignment"` via the frontend UI.
2. **AI Categorization & Routing:**
   The backend extracts the items, identifies it as moderate risk, and creates a `Pending` card in Notion.
3. **Human Approval in Notion:**
   Open Notion, change the card's `status` dropdown to **`Approved`**.
4. **Autonomous Poller Execution:**
   Within 10 seconds, the poller detects the status update, decrements inventory in `backend/data/inventory.json`, creates an entry in the **Run Log** database, and marks the card as `Processed`.
5. **Telegram Dispatch:**
   A Telegram alert with full component breakdowns and IST timestamp arrives immediately.

---

## 📜 9. License

MIT License — Built for the Hackathon Notion Track.
