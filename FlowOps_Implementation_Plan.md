## Goal Description
The goal is to build FlowOps, a Request → Approval → Action Engine for automating lab component issue/return processes, with a secondary proof-of-concept for restaurant orders. The system will use Astro and Tailwind v4 for the frontend, following Vercel's design language, and FastAPI for the backend to handle AI parsing, routing, and Notion integration.

## User Review Required
> [!IMPORTANT]
> The backend architecture heavily relies on Notion for human-in-the-loop approvals. Please confirm if you have a Notion Workspace and Integration Token ready for this project.

## Open Questions
> [!WARNING]
> 1. The original document mentions hosting the Astro frontend on Cloudflare Pages, but you requested "vercel design md". Are we sticking to Cloudflare Pages for hosting or moving to Vercel?
> 2. Should I set up a mock Notion database for testing, or do you have a live one we can use?
> 3. Do you have API keys for Gemini/Groq ready for the AI Parser component?

## Proposed Changes

---

### Backend Framework (FastAPI)
The core engine responsible for parsing requests, routing them, integrating with Notion, and executing real-world actions.

#### [NEW] backend/main.py
Entry point for the FastAPI application. Sets up routes for `/requests`, `/webhooks/notion`, and `/health`.

#### [NEW] backend/core.py
Manages the generic lifecycle state machine of a request (CREATED → PARSED → ROUTED → PENDING_APPROVAL → EXECUTED → LOGGED).

#### [NEW] backend/parser.py
Handles schema-grounded extraction using Gemini (primary) and Groq (fallback). Responsible for structuring raw text into Pydantic models.

#### [NEW] backend/router.py
Rule-based routing logic to assign risk levels (Normal vs. High) and determine if a request can be auto-approved or needs human intervention in Notion.

#### [NEW] backend/notion_client.py
Wrapper for the Notion API. Handles fetching updates, webhook verification, and fallback polling.

#### [NEW] backend/poller.py
Uses `APScheduler` to run a background job that polls Notion every ~30s as a safety net for missed webhooks.

#### [NEW] backend/schemas/lab.json
Schema definition for the lab equipment domain (e.g., items, quantities).

#### [NEW] backend/schemas/restaurant.json
Schema definition for the restaurant domain (e.g., food items, table numbers).

#### [NEW] backend/actions/lab.py
Executes the real-world action for the lab domain (e.g., updating inventory, notifying the student).

#### [NEW] backend/actions/restaurant.py
Executes the real-world action for the restaurant domain.

---

### Frontend Framework (Astro + Tailwind v4)
The requester-facing UI built with Astro and styled using Tailwind CSS v4, adhering to Vercel's minimalist design principles.

#### [NEW] frontend/package.json
Project configuration, including dependencies for Astro and Tailwind CSS v4.

#### [NEW] frontend/src/pages/index.astro
The main submission form for users to enter their requests in plain text.

#### [NEW] frontend/src/components/RequestForm.astro
A reusable form component styled with Tailwind v4, utilizing high contrast and clean typography (Vercel design system).

#### [NEW] frontend/src/styles/global.css
Global styles, importing Tailwind v4 and Vercel's Geist font.

## Verification Plan

### Automated Tests
Run tests for the backend logic, particularly the AI parser and router:
```bash
cd backend
pytest tests/
```

### Manual Verification
1. Open the Astro frontend in the browser and submit a natural language request (e.g., "I need 2 Arduinos for my lab").
2. Verify that the backend successfully parses the request and creates a Pending card in Notion.
3. Manually approve the request in Notion.
4. Verify that the Action Executor fires (e.g., terminal output logs the inventory change) and a new row is added to the Notion Run Log.
5. Submit an ambiguous request (e.g., "I need some stuff") and verify it creates a "Needs Clarification" card in Notion.
