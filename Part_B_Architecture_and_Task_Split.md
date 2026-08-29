# Part B — Civic Resource Prioritization Platform

## Full Architecture & 3-Way Task Division (12-Hour Build)

---

## 1\. Tech Stack (Final)

| Layer | Choice | Why |
| :---- | :---- | :---- |
| Backend | **Python 3.11 \+ FastAPI** | Native fit for Fuzzy TOPSIS (numpy), Knapsack (DP), SHAP (`shap` lib), pHash (`imagehash`) — no cross-language bridge needed |
| Database | **PostgreSQL** (new Supabase project) | Same infra pattern as Part A, but a fresh, isolated project — no shared tables with Part A |
| Frontend | **React \+ Vite** | Reuse UI *patterns* (forms, dashboards) from Part A visually, but a separate codebase |
| ML/Explainability | **scikit-learn \+ shap** | Real trained model \+ real Shapley values, small dataset is fine — SHAP correctness doesn't depend on model size |
| Image Dedup | **imagehash (Python)** | Real perceptual hashing, off-the-shelf, no need to build from scratch |
| Messaging | **Twilio WhatsApp Sandbox** (or Meta Cloud API test number) | Real WhatsApp messages, no production business verification needed for demo |
| Auth | JWT, simple OTP-style citizen login | Lightweight, reused pattern only (not shared code) from Part A |

---

## 2\. Data Model

wards

  id, name, ward\_number, population, equity\_weight (0-1)

citizens

  id, phone, name, created\_at

tickets

  id, citizen\_id, ward\_id, category, description,

  photo\_url, phash (perceptual hash string),

  lat, lon,

  status (OPEN | DEDUPED | PRIORITIZED | ALLOCATED | DISPATCHED | RESOLVED | DEFERRED),

  duplicate\_of\_ticket\_id (nullable, FK \-\> tickets.id),

  community\_multiplier (int, default 1, incremented on each dedup match),

  criteria\_scores (JSONB: {infra\_criticality, safety\_risk, equity, resource\_cost} as TFN triplets or crisp values),

  topsis\_score (float, nullable until prioritization runs),

  created\_at, updated\_at

criteria\_weights (config table)

  id, criterion\_name, weight\_low, weight\_mid, weight\_high (TFN triplet), criterion\_type (benefit | cost)

daily\_allocations

  id, date, ticket\_id, allocated (bool), budget\_used, workforce\_hours\_used

explanations

  id, ticket\_id, shap\_values (JSONB), nlg\_message (text), generated\_at

whatsapp\_logs

  id, ticket\_id, message\_type (REGISTERED|PRIORITIZED|DEFERRED|DISPATCHED|RESOLVED),

  status (SENT|FAILED), sent\_at

---

## 3\. Service Modules

1. **Ingestion Service** — ticket submission API, photo upload, pHash computation, geospatial+visual dedup check against open tickets within a radius  
2. **Prioritization Engine** — Fuzzy TOPSIS: normalizes criteria matrix, applies AHP weights, computes closeness coefficient per open ticket  
3. **Allocation Engine** — 0/1 Knapsack DP: given daily budget \+ workforce constraints, selects the subset of prioritized tickets to dispatch today  
4. **Explainability Service** — trains a small regression model (features \= criteria scores, target \= topsis\_score) via scikit-learn, runs real SHAP (`TreeExplainer`/`LinearExplainer`) for per-ticket Shapley values, then an NLG layer (template or LLM) converts values into a citizen-facing message  
5. **Notification Service** — sends WhatsApp utility messages (registered/prioritized/deferred/dispatched/resolved) via Twilio Sandbox  
6. **Frontend Dashboard** — admin: ranked ticket list, today's allocation/dispatch view, per-ticket explanation panel. Citizen: submit ticket, track status

---

## 4\. API Contract (defined upfront so all 3 tracks can work in parallel against a fixed interface)

POST   /api/tickets                    → submit new ticket (multipart: photo \+ fields)

GET    /api/tickets?status=\&ward\_id=   → list tickets, filterable

GET    /api/tickets/{id}               → single ticket detail

POST   /api/prioritize/run             → recompute Fuzzy TOPSIS for all OPEN tickets

GET    /api/prioritize/ranked          → ranked list with topsis\_score

POST   /api/allocate/run               → run Knapsack for today's budget/workforce

GET    /api/allocate/today             → today's dispatch manifest

GET    /api/explain/{ticket\_id}        → SHAP values \+ NLG message for a ticket

POST   /api/notify/whatsapp/{ticket\_id} → trigger a WhatsApp message (message\_type in body)

Response shapes (example):

// GET /api/prioritize/ranked

\[

  {

    "id": "uuid",

    "category": "pothole",

    "ward\_id": "uuid",

    "topsis\_score": 0.812,

    "status": "PRIORITIZED",

    "community\_multiplier": 3

  }

\]

// GET /api/explain/{ticket\_id}

{

  "ticket\_id": "uuid",

  "shap\_values": {

    "infra\_criticality": 0.31,

    "safety\_risk": 0.42,

    "equity": 0.05,

    "resource\_cost": \-0.11

  },

  "nlg\_message": "Your request has been prioritized for immediate action due to high risk to public safety..."

}

This contract is the seam between the three tracks below — everyone builds against it from hour 0, so integration at checkpoints is fast.

---

## 5\. Three-Way Task Split (12 hours)

### Track 1 — YOU (solo dev): Core Algorithms Engine

**Why you own this:** this is the differentiator judges will question hardest. You need to genuinely understand and be able to defend Fuzzy TOPSIS, the Knapsack constraint model, and how SHAP is computed — that's much harder to do convincingly if an assistant wrote it and you're improvising explanations live.

**Build:**

- Fuzzy TOPSIS module (`prioritization.py`): normalized fuzzy decision matrix, weighted matrix, FPIS/FNIS, closeness coefficient  
- Knapsack module (`allocation.py`): 0/1 DP with budget \+ workforce dual constraints  
- Explainability module (`explain.py`): train small sklearn model on criteria→topsis\_score, run real SHAP, output per-feature Shapley values  
- Unit tests with hand-checkable small examples (3-5 tickets) so you can verify the math is right and explain it confidently

**Hours 0–6.5** (matches earlier 12-hour plan for these 3 pieces)

---

### Track 2 — Assistant 1 (Claude Code / Antigravity session): Backend Infrastructure

**Build:**

- FastAPI project scaffold, DB schema/migrations (section 2 above), Supabase connection  
- `POST /api/tickets` — ticket submission incl. photo upload to storage  
- pHash dedup logic (`imagehash` library) — compute hash on upload, compare Hamming distance against open tickets in same ward/radius, auto-link duplicates \+ increment `community_multiplier`  
- WhatsApp integration (Twilio Sandbox) — `POST /api/notify/whatsapp/{ticket_id}`, message templates for each status  
- Wire in Track 1's algorithm modules once ready (import as internal functions, expose via `/api/prioritize/run` and `/api/allocate/run`)

**Prompt this assistant with:** the API contract in Section 4, the data model in Section 2, and explicitly: *"Build the endpoints to match this contract exactly. The prioritization and allocation logic will be provided separately — stub them with a placeholder function that returns mock scores for now, so the rest of the API is testable independently."*

---

### Track 3 — Assistant 2 (Claude Code / Antigravity session): Frontend \+ Demo Data

**Build:**

- React dashboard: ranked ticket list (sortable by `topsis_score`), today's allocation view (from `/api/allocate/today`), per-ticket explanation panel (from `/api/explain/{id}`, rendered as a simple bar chart of SHAP contributions \+ the NLG message)  
- Citizen-facing submission form: category, description, photo upload, GPS capture  
- **Realistic Kopargaon demo data seed script**: \~25-30 tickets across categories (potholes, drainage, garbage, water contamination, bridge/flood-adjacent issues) spread across real ward names, written in the same tone/context style as Part A's flood research data — so the demo narrative feels connected to the same city, not generic filler

**Prompt this assistant with:** the API contract in Section 4, and explicitly: *"Build all UI against this exact contract using mock/sample JSON matching the response shapes shown, so the frontend is fully functional and demoable even before the real backend is wired in."*

---

## 6\. Integration Checkpoints

| Hour | Checkpoint |
| :---- | :---- |
| 4 | Track 1: TOPSIS \+ Knapsack logic tested standalone. Track 2: ticket submission \+ dedup working. Track 3: dashboard renders against mock data |
| 8 | Track 2 wires in Track 1's real algorithm modules. Track 3 points at real API instead of mocks. WhatsApp sandbox sending real messages |
| 10.5 | Full end-to-end run: submit tickets → dedup → prioritize → allocate → explain → notify, all real, no mocks left anywhere |
| 11–12 | Bug fixes, seed final demo data, pitch prep |

---

## 7\. Non-Negotiable Honesty Notes for the Pitch

- SHAP values are **real Shapley values** from a real (small) trained model — the model being small does not make the SHAP computation fake. State this plainly if asked.  
- WhatsApp messages are sent through a **sandbox/test number** — real API, real messages, just not yet Meta-verified for public production use. Say so if asked.  
- Fuzzy TOPSIS weights (AHP) are **your own reasonable defaults** for this MVP, not literally derived from a live municipal expert panel — say this is the intended real-world calibration step, currently using informed placeholder weights.

