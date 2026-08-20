# FlowOps — Request → Approval → Action Engine
### Final Hackathon Plan — Notion Track

---

## 1. Positioning (read this before anything else)

The problem statement is explicit: **"One job killed cleanly beats five half-wired ideas."** So the pitch is NOT "we automate every kind of request." It is:

> **"We killed one real job — college lab equipment issuing — with a properly engineered request/approval/action engine. The engine is generic by design, and we prove that by adapting it to a second domain live in the demo."**

**Job (what judges score):** Lab component issue/return automation.
**Architecture (what makes it impressive):** Built as a reusable engine, not a one-off script — proven with one additional domain, not four.

Do not present "Lab / Parking / Cafe / Club" as four equal features. Present one deep flagship + one short reusability proof.

---

## 2. Core Loop

> **Sender raises a request → AI structures it → rules route it → Notion holds the human decision → code executes the real action → everything is logged.**

```
CREATED → PARSED → ROUTED → PENDING_APPROVAL → (APPROVED|REJECTED) → EXECUTED → LOGGED
```

Every transition is automatic except one: the human decision inside Notion.

---

## 3. Architecture

```
                    Astro (requester-facing form)
                              │
                              ▼
                         FastAPI (engine)
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              AI Parser    Router    Notion Client
           (Gemini/Groq)  (if/else)      │
                    │                     ▼
                    └──────────────►  Notion DB
                                    (Pending card)
                                          │
                                          ▼
                                  Human: Approve/Reject
                                  (Notion button/property)
                                          │
                         ┌────────────────┘
                         ▼
              Notion Webhook (page.property_values.updated)
              + polling fallback every ~30s (safety net)
                         │
                         ▼
                  Action Executor (domain module)
                         │
                         ▼
                    Real-world action
                         │
                         ▼
                    Run Log (Notion, written by integration token)
```

- **Astro** = requester-facing submission UI only. Not a duplicate operator dashboard.
- **LLM Engine**: Gemini (via python SDK) for intelligent parsing.
- **Notion** = the only operator interface. Pending queue, approve/reject, override, Run Log — all live here.
- **FastAPI** = the actual engine. Owns parsing, routing, execution, logging.

---

## 4. Data Model

### Requests DB (Notion)
| Field | Type | Notes |
|---|---|---|
| `request_id` | text | unique |
| `domain` | select | lab (primary) / restaurant (proof-of-reusability) |
| `sender_id` | text | requester |
| `receiver_id` | text | approver, set by router |
| `event_type` | select | e.g. "issue component", "return component" |
| `details` | JSON/rich text | structured payload from parser |
| `status` | select | Pending / Approved / Rejected / Needs Clarification / Auto-Approved |
| `risk_level` | select | Normal / High (drives adaptive approval, see §7) |
| `created_at` / `resolved_at` | date | timestamps |

### Run Log DB (Notion)
`request_id`, `action_taken`, `actor` (system/human), `timestamp`, `result` — written only via integration token, never typed manually (judges check attribution).

---

## 5. Backend Structure (FastAPI)

```
/backend
  main.py                → routes: /requests, /webhooks/notion, /health
  core.py                → generic lifecycle state machine
  parser.py               → schema-grounded structured extraction (see §6)
  router.py               → pure rule-based receiver + risk assignment
  notion_client.py        → Notion API wrapper, webhook verification, polling fallback
  schemas/
    lab.json
    restaurant.json
  actions/
    lab.py                 → inventory update, notify student
    restaurant.py           → kitchen notify, order status update
  poller.py                → APScheduler job, safety-net for missed webhooks
```

Every `actions/*.py` implements one interface:
```python
def execute(request: Request) -> ActionResult: ...
```
New domain = one action file + one schema file. Core untouched.

---

## 6. AI Parsing — Schema-Grounded Extraction, Not Full RAG

**Decision: skip vector DB/embeddings.** This is extraction against a known schema, not open-ended knowledge lookup — a full RAG pipeline would add complexity without benefit here.

Flow:
```
raw text + domain
        │
        ▼
load schemas/{domain}.json  (retrieval = simple lookup, not vector search)
        │
        ▼
prompt = system instructions + JSON schema + 1-2 examples + user text
        │
        ▼
Gemini structured output (primary) — native JSON schema enforcement
Groq (fallback) — faster, use if Gemini is down during demo
        │
        ▼
Pydantic validation
        │
   ┌────┴────┐
 valid     invalid/incomplete
   │           │
   ▼           ▼
Router    status = "Needs Clarification" → Notion card, human resolves
```

Always include a `missing_fields` / `needs_human_clarification` field in the output schema — this turns ambiguous input into a clean "Needs Clarification" card in Notion instead of a bad guess or crash. This is a strong failure-handling demo moment.

**Reserve true RAG** (retrieving lab policy docs, experiment requirements, approval rules) as a stated future extension, not something to build under time pressure.

---

## 7. Adaptive Approval (added strength from review)

Not every request needs a human. Let the router apply a risk rule before deciding whether to auto-approve or send to Notion for approval:

```python
if domain == "lab" and item_qty <= NORMAL_THRESHOLD and known_component:
    risk_level = "Normal" → auto-approve, log, execute immediately
else:
    risk_level = "High" → Notion Pending, human required
```

Example: 1 Arduino → auto-approved and logged. 50 Arduinos, or an unlisted component → flagged for human approval. This upgrades the system from "approval queue" to "autonomous when safe, human-controlled when it matters" — a meaningfully stronger story for judges than blanket manual approval.

---

## 8. Escalation

```
Request pending > N minutes
        │
        ▼
Reminder logged
        │
        ▼
Still pending > threshold
        │
        ▼
Escalate to secondary approver, log escalation event
```

Keep this — it's what turns a CRUD approval form into an actual workflow engine.

---

## 9. Failure Handling (make this part of the live demo)

- Ambiguous input ("need some electronics stuff tomorrow") → `needs_human_clarification: true` → Notion "Needs Clarification" card, not a crash or a bad guess.
- Duplicate requests → deduplicated by sender + time window.
- No response within threshold → escalation (§8), never silently dropped.

Deliberately submitting a bad request live is a strong judge moment — show the system degrade gracefully, not fail.

---

## 10. Notion Integration — Webhook + Polling Hybrid

Verified: Notion API webhooks (`page.property_values.updated`) shipped in the 2026-03-01 API version and are usable for this purpose. Two caveats to design around:
- **Payloads are sparse** — a webhook tells you *something* changed; your backend still needs a follow-up API call to fetch the actual new status.
- **Still maturing / beta-adjacent** — don't rely on webhooks alone for a live demo.

**Design:** webhook as the primary trigger for responsiveness, **plus** a lightweight poller (`APScheduler`, ~20–30s interval) as a safety net that would still work even if the webhook silently failed. This hybrid is worth stating explicitly in the PPT as a deliberate reliability decision, not an oversight.

---

## 11. Tech Stack (final)

| Layer | Tech | Reasoning |
|---|---|---|
| Requester UI | Astro | Lightweight, deploys to Cloudflare Pages, doesn't duplicate Notion |
| Engine | Python + FastAPI | Async, clean webhook endpoints |
| Scheduler | APScheduler | Polling fallback for Notion status |
| AI parsing | Gemini (primary, structured output) + Groq (fallback) | Schema-grounded extraction, no RAG needed |
| Notion integration | `notion-client` SDK + Notion API webhooks | Requests DB + Run Log, integration-token attribution |
| Real actions | Domain-specific (e.g. inventory update function, WhatsApp/email confirmation) | Must be a real outside-world change |
| Frontend hosting | Cloudflare Pages (Astro) | First-class Astro support |
| Backend hosting | Render / Railway / Fly.io (normal Python runtime) | Avoid Cloudflare Python Workers for the core engine — still beta/WASM-based, adds dependency risk you don't need under time pressure |

---

## 12. Build Plan Across the Event

| Day | Milestone |
|---|---|
| Day 1 | Notion schema (Requests + Run Log) finalized. Core engine skeleton. Lab domain wired end-to-end using existing lab management project as the base. |
| Day 2 | Parser (schema-grounded, Gemini) + router + adaptive approval logic. Webhook + polling hybrid working. Run Log populating live. |
| Day 3 | Escalation + failure handling (clarification flow, duplicates). Second domain (restaurant) added as a short reusability proof — same engine, new action file + schema only. |
| Final hours | Demo rehearsal, Notion workspace polish (clean titles, no raw JSON), PPT finalized. |

Commits and Run Log rows should be visibly spread across all days — explicitly judged.

---

## 13. Demo Script

1. Backend off → show Notion workspace is still a readable, useful operations hub on its own.
2. Backend on → submit a real lab request via Astro form.
3. Show AI-parsed, human-readable Pending card appear in Notion.
4. Approve live in Notion → real action fires (inventory decremented, confirmation sent) → Run Log row appears with a genuine timestamp.
5. Submit a deliberately ambiguous request → show it become a "Needs Clarification" card instead of crashing.
6. Submit a small, normal request → show it auto-approve via the adaptive risk rule, no human needed.
7. Switch domain to restaurant → submit "2 butter chicken, table 12" → same engine, new action module → order confirmed, logged. This is the reusability proof — kept short, not a second full demo.
8. Close with the "delete the repo" framing: without the code, nothing in this loop would run — Notion alone is static data.

---

## 14. PPT Outline

1. The problem — requests scattered across WhatsApp/paper/forms, no audit trail.
2. The insight — every version of this problem is the same shape: Request → Approval → Action → Audit.
3. The job we killed — lab equipment issuing (be specific and concrete here).
4. Architecture — trigger → AI parser → router → Notion → human → action → Run Log.
5. Deep demo — lab flow, full detail.
6. Reusability proof — same engine, restaurant domain, 20 seconds.
7. AI's actual role — parsing/drafting only; routing and execution stay rule-based.
8. Adaptive approval + escalation — autonomous when safe, human-controlled when it matters.
9. Failure handling — clarification flow, duplicates, no silent drops.
10. Why Notion — operations hub, approval layer, and audit trail in one place.
11. What's next — new domains are a schema file + action module away, not a rewrite.

---

## 15. Checklist Against Judging Criteria

- Runs without a human operator — Astro/webhook trigger, deployed, not run manually.
- Human approval inside Notion — required for high-risk/ambiguous requests.
- Real-world action — inventory update / confirmation, not just a dashboard change.
- Proof via Run Log — timestamped, integration-token-attributed, spread across days.
- AI used only where rules can't — parsing and clarification detection, never routing or approval logic.
- One job, cleanly killed — lab flow is the hero; restaurant is a proof, not a second product.
