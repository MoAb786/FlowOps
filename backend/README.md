# FlowOps - Backend Engine

FastAPI-powered backend engine for FlowOps that parses natural language requests using Groq LLM, routes them according to domain-specific risk criteria, and syncs status with Notion databases.

---

## 🛠️ Prerequisites

- **Python 3.10+**
- **Groq API Key** (for LLM request extraction)
- **Notion Integration Token & Database ID** (for ticketing/request tracking)

---

## 🚀 Quick Start Setup

### 1. Navigate to the backend directory
```bash
cd backend
```

### 2. Create and activate a virtual environment

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (cmd / PowerShell):**
```bash
python -m venv venv
# PowerShell:
.\venv\Scripts\Activate.ps1
# CMD:
.\venv\Scripts\activate.bat
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note:** If you want to install only the core FlowOps service packages without optional robotics/ROS packages, you can run:
> ```bash
> pip install fastapi uvicorn python-dotenv groq notion-client pydantic httpx
> ```

### 4. Configure Environment Variables
Copy the `.env.example` file to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```dotenv
GROQ_API_KEY=gsk_your_groq_api_key_here
NOTION_API_KEY=ntn_your_notion_integration_token_here
NOTION_REQUESTS_DB_ID=your_notion_database_id_here
```

---

## 🏃 Running the Server

Start the FastAPI application with auto-reload:

```bash
python main.py
```
*or directly using Uvicorn:*
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be accessible at:
- **Base URL:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check endpoint |
| `POST` | `/requests` | Parse, route, and process/escalate a natural language request |
| `POST` | `/webhooks/notion` | Webhook receiver for updates from Notion |

### Example Request (`POST /requests`):
```bash
curl -X POST http://localhost:8000/requests \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I need 2 Arduinos for my lab tomorrow",
    "domain": "lab",
    "sender_id": "user_123"
  }'
```

---

## 📁 Project Structure

```text
backend/
├── actions/            # Domain-specific execution handlers (e.g. lab, restaurant)
│   ├── lab.py
│   └── restaurant.py
├── schemas/            # JSON schemas for structured LLM parsing
│   ├── lab.json
│   └── restaurant.json
├── core.py             # Orchestration logic (Parse -> Route -> Approve/Log)
├── main.py             # FastAPI entrypoint and route definitions
├── notion_helper.py    # Notion API async client integration
├── parser.py           # Groq LLM structured JSON extractor
├── router.py           # Domain risk-assessment & approver routing
├── .env.example        # Environment variable template
└── requirements.txt    # Python package dependencies
```

