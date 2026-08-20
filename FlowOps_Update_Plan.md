# FlowOps — Post-Analysis Update Plan

Source: analysis.md gap review against Notion Track theme.
Priority order below matches judging risk, highest first.

---

## Fix 1 — Make the external action real (HIGHEST PRIORITY)

**Problem:** `backend/actions/lab.py` only prints to stdout. No real-world state changes. Fails the theme's explicit test: *"If nothing changes in the real world, you built a dashboard."*

**Fix:** Give `lab.py` (and `restaurant.py`) a genuine external side effect. Cheapest reliable options for hackathon time constraints, in order of recommendation:
1. A real local inventory store (SQLite or JSON file) that actually decrements/increments on issue/return — verifiable by opening the file before/after.
2. A generated PDF issue receipt/gate-pass per approved request (using a lightweight lib).
3. A Discord/Slack/Telegram webhook notification to the requester — free, fast to wire, visibly "real" in a live demo.

Recommend doing **both** #1 (inventory persistence, satisfies "state changed") and #3 (notification, satisfies "message sent") since together they're the strongest demo moment and not much extra work.

## Fix 2 — Human-readable Notion cards, not raw JSON

**Problem:** `notion_helper.py` writes `json.dumps(details)` directly into the card. Theme explicitly calls this out as a common mistake.

**Fix:** Add a formatting function that converts the structured `details` dict into clean bullet-point text before writing to Notion (e.g. `"• 2x Arduino Uno\n• 1x Breadboard\nReason: Lab assignment"`). Also format the card title as something readable (e.g. `"Lab Request — Rohan — 2x Arduino Uno"`), not an ID string.

## Fix 3 — Clarify dashboard.astro's role

**Problem:** Risk of it becoming a duplicate operator interface, which the theme explicitly forbids ("a person has to be able to do their whole part of the job inside Notion").

**Fix:** Reframe as strictly a **read-only requester tracking view** — "here's the status of requests I submitted." No approve/reject/edit controls anywhere in Astro. All management stays in Notion.

## Fix 4 — Spread commits and Run Log rows over time

Not a code change — a working-habit change for the rest of the build. Commit incrementally each work session; avoid generating Run Log rows in one batch right before submission, since attribution/timestamps are checked.

---

## Prompt to give your CLI coding agent

Paste this directly:

```
I need to fix 3 gaps in my FlowOps project found during a theme-alignment review @analysis.md on comparing project with @Theme - Notion Track.pdf.
Make these changes:

1. backend/actions/lab.py and backend/actions/restaurant.py currently only
   print logs to stdout. Replace this with a real external side effect:
   - Add a persistent inventory store (SQLite, a new backend/inventory.db,
     or a JSON file backend/data/inventory.json) that actually increments/
     decrements component quantities when a request is issued or returned.
   - Also send a real notification on approval — implement a webhook call
     to Discord (or Slack, whichever is simpler to set up) using an
     incoming webhook URL from an environment variable, sending a short
     human-readable message like "Request REQ-104 approved: 2x Arduino Uno
     issued to Rohan."
   - Wire both of these into the existing execute(request) function for
     each domain, keeping the same function signature.

2. backend/notion_helper.py currently writes json.dumps(details) directly
   into the Notion card body/details property. Replace this with a
   formatting function format_details_for_humans(details: dict) -> str
   that converts the structured dict into clean bullet-point text, e.g.:
     • 2x Arduino Uno
     • 1x Breadboard
     Reason: Lab assignment
   Also update the card title generation to be human-readable, e.g.
   f"Lab Request — {sender_id} — {item_summary}" instead of just the
   request_id. Use this formatter everywhere details get written to Notion,
   including the Run Log entries.

3. frontend/src/pages/dashboard.astro should be strictly a read-only
   tracking view for the requester (status of requests they submitted).
   Remove or disable any approve/reject/edit controls if present — those
   must only exist in Notion. Add a clear note in the page or component
   that this is a tracking view only.

After making these changes, show me a diff summary of what changed in each
file so I can verify before committing.
```

---

## Verification checklist after the CLI applies changes

- [ ] Open the inventory file/DB before and after a demo request to confirm the number actually changed.
- [ ] Trigger a Discord/Slack notification and confirm it arrives with readable text, not raw JSON.
- [ ] Open a Notion card and confirm it reads as clean bullet points + a readable title, not a JSON blob.
- [ ] Confirm dashboard.astro has no way to approve/reject anything — only Notion does.
- [ ] Commit these changes now, and continue committing incrementally rather than batching near the deadline.
