# 1. Overview

**Product**: AIMhi‑Y Supportive Yarn Chatbot (Web Prototype)

**Goal**: Deliver a culturally safe, rule‑first chatbot that walks young people through the AIMhi Stay Strong 4‑step model (support people → strengths → worries → goals), detects risk language reliably, and provides an optional, tightly‑bounded LLM fallback for genuinely open‑ended inputs.

**Primary users**: Aboriginal and Torres Strait Islander young people (12–25) engaging with AIMhi or the Stay Strong website in a demo context (no production release or clinical use).

**Sponsors/Stakeholders**: Menzies School of Health Research (AIMhi/Stay Strong team), CDU (course assessors), Group 36.

**Non‑clinical status**: Prototype only; no diagnosis or crisis handling beyond deterministic referral messaging.

By 'support people', we mean the following in this document: The chatbot asks the user about the **people in their life who support them** — such as family, friends, elders, or community members.

---

# 2. Objectives & Key Results (OKRs)

**O1. Engagement via guided conversation**

- KR1: ≥80% of test sessions progress through all 4 steps at least once.
- KR2: Median time to complete 4‑step flow ≤ 6 minutes.

**O2. Safety & compliance alignment**

- KR3: 100% of inputs containing seeded risk phrases trigger the risk protocol within 1 exchange.
- KR4: 0 storage of PII by default; all logs anonymised.

**O3. Lightweight, extensible architecture**

- KR5: Rule/FSM path median backend latency ≤ 500 ms on free hosting.
- KR6: Optional LLM fallback callable behind a single interface with timeouts and guardrails.

---

# 3. Scope

**In scope**

- Guided conversational flow that mirrors AIMhi’s 4‑step model.
- Rule‑based FSM logic with culturally safe, plain‑English prompts.
- Risk keyword detection and deterministic escalation message (links/phone numbers provided by AIMhi “Get Help” page content, configured statically).
- Lightweight NLP: spaCy matcher + lemmatisation + (optional) sentiment for nuance.
- Dispatcher that routes each message to FSM, NLP intent handlers, or LLM fallback.
- Simple web UI (HTML + Bootstrap + JS) talking to a Flask API.
- Optional SQLite chat‑history store (required if LLM fallback enabled) with anonymous `session_id`.
- Basic telemetry (counts only; no PII), feature‑flagged.

**Out of scope**

- Live integration with AIMhi app/website, clinical deployment, user accounts, PII collection, analytics beyond aggregate counts, or human‑in‑the‑loop moderation.

**Assumptions**

- All content copy is pre‑approved and culturally appropriate.
- Free‑tier hosting is acceptable for demo; cold starts are tolerated.

---

# 4. User Stories

- **U1. Guided session**: As a young person, I can follow a clear, supportive chat through the 4 steps and finish with a simple goal statement.
- **U2. Risk detection**: As a user in distress, if I type certain phrases, I am immediately shown a calm message with crisis resources and a pause in regular flow.
- **U3. Flexibility**: As a user who types freely, the bot still responds helpfully even if my input doesn’t match the current step (fallback/clarifier/LLM).
- **U4. Educator/Stakeholder demo**: As a stakeholder, I can run a short demo without setup and see the flow, risk handling, and documentation.

---

# 5. Non‑Functional Requirements

- **N1. Privacy-first**: No PII; session IDs are random, ephemeral. Storage is opt‑in.
- **N2. Safety copy**: Prominent disclaimer: not a crisis service; provide emergency contacts.
- **N3. Performance**: Rule path ≤ 500 ms p50; LLM fallback ≤ 3 s p90 (with timeout/abort at 6 s).
- **N4. Reliability**: Graceful degradation if NLP/LLM fails; FSM remains usable.
- **N5. Accessibility**: WCAG‑aligned contrast, keyboard navigation, aria labels.
- **N6. Cultural tone**: Plain English, strengths‑based, non‑judgmental language.

---

# 6. Safety & Standards Alignment

- **Deterministic risk protocol** (no ML gating). Immediate switch to resource message, halt standard flow, present phone numbers and links (config‑driven).
- **Hard filters** for disallowed outputs; LLM responses post‑processed with regex/allow‑list.
- **Content boundaries**: No clinical advice; reflect program guidance only.

---

# 7. System Architecture

**Frontend**: HTML + Bootstrap + Vanilla JS (single page).\
**Backend**: Python Flask API.\
**Logic**: FSM with `transitions` library + spaCy pipeline (matcher/lemmatisation).\
**Optional LLM**: Fine‑tuned small causal model (e.g., GPT‑2 small / Phi‑1.5) via local inference or HF Inference; guarded by router and output sanitizer.\
**Storage**: None by default; optional SQLite for chat history (required only for LLM context).\
**Hosting**: Render or Replit (free tier acceptable for demo; paid to avoid sleep).

**High‑level flow**

```
Browser (HTML/Bootstrap/JS)
   → POST /chat {session_id, message}
      → Router
         ├─ Risk Detector (spaCy PhraseMatcher)
         │    └─ Risk Response (stop flow, show resources)
         ├─ FSM Handler (rule‑first step logic)
         ├─ NLP Intent (simple classifier/matcher) → FSM-compatible reply
         └─ LLM Fallback (guardrailed, optional; uses recent N turns from DB)
   ← JSON {reply, step, flags}
```

---

# 8. Conversation Design

**Core steps**

1. Support people → 2) Strengths → 3) Worries → 4) Goal

**Entry**: Purpose statement + consent to proceed + non‑crisis disclaimer.\
**Exit**: Summarise supports/strength/goal; offer to export summary (on‑screen only).\
**Recovery**: If off‑topic at any step, provide empathetic redirect or clarifying prompt.

**Risk protocol**

- Trigger: match any phrase in curated list incl. synonyms/fuzzy variants (e.g., "suicide", "end it all", "kill myself", "I don't want to live").
- Action: Immediately send resource block (helplines, site links), stop normal FSM until user explicitly continues.

---

# 9. NLP Pipeline (Lightweight)

- **Normalisation**: lowercase, trim, collapse whitespace.
- **spaCy**: `en_core_web_sm` for tokenisation + lemmatisation + PhraseMatcher.
- **Fuzzy match**: `rapidfuzz` for near‑match on risk terms and step synonyms.
- **(Optional)** Sentiment: TextBlob polarity to inform empathetic templates.

**Seed lists (config)**

- Risk terms & phrases (curated; versioned JSON).
- Step‑synonyms (e.g., goal=aim/plan/target; strengths=good at/proud of).

---

# 10. Message Router (Dispatcher)

**Decision order** (short‑circuit on first match):

1. **Risk check** → risk response.
2. **FSM step gate** → if message fits current step (via rules + synonyms), stay in FSM.
3. **Intent/matcher** → map to known intents that progress or clarify the step.
4. **Fallback** → if open‑ended/low confidence and LLM enabled ⇒ call LLM with last *N* turns; else send empathetic generic + clarifier.

**Pseudocode**

```python
def route(msg, session):
    text = normalise(msg)
    if is_risk(text):
        return risk_response()
    if fsm_accepts(text, session.state):
        return fsm_reply(text, session)
    intent, conf = classify_intent(text)
    if conf >= 0.8:
        return handle_intent(intent, session)
    if LLM_ENABLED and conf < 0.4:
        history = get_recent_history(session.id, n=6)
        reply = llm_reply(history + [text])
        return sanitise(reply)
    return empathetic_clarifier()
```

---

# 11. Data Model (optional, for LLM context)

**Tables**

```sql
CREATE TABLE chat_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT CHECK(role IN ('user','bot')) NOT NULL,
  message TEXT NOT NULL,
  ts DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_session_ts ON chat_history(session_id, ts);
```

**Notes**

- `session_id` is random UUID set in a cookie/localStorage; no names/emails stored.
- Truncate history per session (e.g., keep last 100 turns) to bound prompt size.

---

# 12. API Design

- `POST /chat` → `{ session_id, message }` → `{ reply, state, flags }`
- `GET /health` → health check for hosting platform.
- (Optional) `GET /history?session_id` → last N turns (debug only; gated by env var).

**Error handling**: Always return a safe generic reply on 5xx; log server errors without message bodies when `PRIVACY_STRICT=true`.

---

# 13. Content & UX Requirements

- **Tone**: Warm, strengths‑based, plain English. Avoid clinical jargon.
- **Microcopy**: Intro disclaimer, step prompts, empathetic clarifiers, risk message.
- **UI**: Single column, readable fonts, message bubbles, visible step indicator, large tap targets, persistent “Get Help” button.
- **Accessibility**: Labels for inputs, focus states, aria‑live for new messages.

---

# 14. Guardrails & Output Filtering

- Allow‑list of safe response templates for FSM and intent handlers.
- LLM outputs post‑processed with regex filters; if filtered → serve fallback template.
- Strict max‑tokens/length for LLM responses.

---

# 15. Deployment & Environments

- **Local**: `flask run` with `.env` flags; SQLite file ignored by VCS.
- **Staging/Demo**: Render/Replit free tier (autosleep acceptable). Custom domain optional.
- **Always‑on (optional)**: Paid tier or VPS (Hetzner/Contabo) with `gunicorn` + `nginx`.

**Env flags**: `LLM_ENABLED`, `PRIVACY_STRICT`, `HISTORY_ENABLED`, `MAX_HISTORY=6`.

---

# 16. Testing Strategy

- **Unit**: FSM transitions, risk detector, router branching, content templates.
- **Integration**: End‑to‑end chat happy path + off‑path; LLM timeout and fallback.
- **Safety tests**: Exhaustive risk phrase list; fuzzed misspellings; ensure deterministic escalation.
- **UX/Accessibility**: Keyboard navigation, screen‑reader checks, mobile viewport.

---

# 17. Analytics (non‑PII, opt‑in)

- Session count, completion rate of 4 steps, risk‑trigger count, average turns per session.
- No IPs, no user agents, no message content in telemetry.

---

# 18. Delivery Plan & Milestones

- **M1 (Week 1)**: FSM + core prompts + web UI shell + /chat endpoint.
- **M2 (Week 2)**: spaCy matcher + router + risk protocol + accessibility pass.
- **M3 (Week 3)**: Optional LLM fallback + SQLite context + guardrails.
- **M4 (Week 4)**: Testing, docs, demo build, stakeholder walkthrough.

---

# 19. Risks & Mitigations

- **Cold starts** on free hosting → communicate in demo; keep lightweight assets.
- **Over‑triggering risk** → tune lists; require phrase+sentiment for some matches (configurable).
- **LLM drift** → keep LLM optional; post‑filter; prefer templates.
- **Scope creep** → feature flags; v2 backlog.

---

# 20. Backlog (Post‑MVP)

- Multilingual variants; progressive web app shell; export/share session summary; admin content editor for prompts; co‑design user testing; model cards and data sheets for any fine‑tuned models.

---

# 21. Acceptance Criteria (Go/No‑Go)

- Completes 4‑step flow with guardrails and risk protocol working deterministically.
- Passes unit/integration tests; no PII stored; demo deploy accessible publicly.
- Documentation delivered: README, setup guide, architecture diagram, safety notes.

