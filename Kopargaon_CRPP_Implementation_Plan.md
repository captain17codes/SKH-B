# Implementation Plan: Kopargaon Civic Resource Prioritization Platform (CRPP)

**From strategic framework to buildable system**
Companion engineering document to *"Strategic Framework for Intelligent Civic Resource Allocation and Triage in Kopargaon Municipal Council."*
Version 1.0 — Draft for Chief Officer / IT Cell review

---

## 1. How to Read This Plan

The source report specifies the **logic** (Fuzzy AHP → Fuzzy TOPSIS → Knapsack RCPSP → SHAP → WhatsApp). This plan specifies the **system**: what gets built, in what order, with which technologies, by whom, on what data, exposed through which APIs, deployed how, and validated against what tests. It is organized as:

1. System architecture
2. Data model (schema-level)
3. Module-by-module build spec (with working algorithm code)
4. API contract
5. Infrastructure & deployment
6. Security, compliance, and audit design
7. Testing & validation strategy
8. Phased delivery roadmap with timeline
9. Team, roles, and indicative cost
10. Risk register

---

## 2. System Architecture

### 2.1 High-level component diagram (textual)

```
┌────────────────────┐      ┌─────────────────────┐
│  Citizen Channels   │      │  Municipal Staff /   │
│  - WhatsApp Business│      │  Chief Officer Portal │
│  - Web/Android form  │      │  (Admin Dashboard)   │
└─────────┬───────────┘      └──────────┬───────────┘
          │  webhook / REST             │  REST (auth)
          ▼                              ▼
┌────────────────────────────────────────────────────┐
│               API Gateway (NGINX / Kong)             │
└─────────┬───────────────────────────────┬───────────┘
          ▼                               ▼
┌────────────────────┐         ┌───────────────────────┐
│ Ingestion Service    │        │  Auth & RBAC Service   │
│ - Validate payload    │        │  (JWT, ward-level ACL)│
│ - GPS normalize       │        └───────────────────────┘
│ - Media upload → S3   │
└─────────┬─────────────┘
          ▼
┌────────────────────────┐
│ Deduplication Service    │  ← pHash + geo-radius match
│ (Python, imagehash)      │
└─────────┬─────────────────┘
          ▼
┌────────────────────────┐
│ Ticket Store (Postgres)  │◄────────────┐
└─────────┬─────────────────┘             │
          ▼                                │
┌────────────────────────┐                │
│ MCDA Engine               │               │
│ - Fuzzy AHP (weights)      │              │
│ - Fuzzy TOPSIS (CCi score) │              │
└─────────┬─────────────────┘              │
          ▼                                │
┌────────────────────────┐                │
│ Knapsack Optimizer         │              │
│ (OR-Tools CP-SAT / ILP)    │              │
│ → Daily Dispatch Manifest  │─────────────┘
└─────────┬─────────────────┘
          ▼
┌────────────────────────┐
│ Explainability Service     │  ← SHAP (KernelExplainer/TreeExplainer)
│ + NLG templater             │
└─────────┬─────────────────┘
          ▼
┌────────────────────────┐
│ Notification Service       │  ← WhatsApp Business API (Cloud API)
│ (queue-driven, retries)     │
└────────────────────────┘

Cross-cutting: Audit Log Service (immutable, hash-chained) — reads from
every stage above; feeds the RTS Appeal Defense export.
```

### 2.2 Why this shape

- **Ingestion and dedup are decoupled from scoring.** Perceptual-hash matching is cheap and must run before a ticket ever reaches the MCDA engine, or the "community severity multiplier" logic breaks (Phase 1 of the source report).
- **MCDA engine and Knapsack optimizer are separate services**, not one monolith, because they run on different cadences: TOPSIS scores can be recomputed continuously as new evidence arrives (fuzzy bounds narrowing), while the Knapsack allocation is a **daily batch job** that consumes current budget/workforce constraints and the latest CCi scores.
- **Explainability is a first-class service, not a UI afterthought.** SHAP values must be computed and stored at the same time a ticket is included/excluded from a dispatch manifest, so the NLG message and the audit record are generated from the same object.
- **Audit log is append-only and hash-chained** so it can serve as legally defensible evidence under the RTS Act (see §6.3).

---

## 3. Data Model

### 3.1 Core entities (PostgreSQL + PostGIS)

```sql
-- Citizens (minimal PII, phone-number keyed for WhatsApp)
CREATE TABLE citizens (
    citizen_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number    VARCHAR(15) UNIQUE NOT NULL,
    ward_id         INT REFERENCES wards(ward_id),
    consent_ts      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE wards (
    ward_id         SERIAL PRIMARY KEY,
    ward_name       TEXT NOT NULL,
    geom            GEOMETRY(POLYGON, 4326),
    equity_index    NUMERIC(4,3)  -- 0..1, drives C3 (Socio-Spatial Equity)
);

-- Grievance tickets
CREATE TABLE tickets (
    ticket_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id           UUID REFERENCES citizens(citizen_id),
    ward_id               INT REFERENCES wards(ward_id),
    category               TEXT NOT NULL,  -- pothole, waterlogging, sanitation, water_quality...
    description             TEXT,
    location                GEOMETRY(POINT, 4326) NOT NULL,
    status                    TEXT NOT NULL DEFAULT 'open',  -- open, deduped, scored, dispatched, resolved, deferred
    parent_ticket_id       UUID REFERENCES tickets(ticket_id),  -- set if deduped into another
    community_multiplier   NUMERIC(4,2) DEFAULT 1.0,
    sla_deadline             TIMESTAMPTZ,  -- derived from RTS category (21–45 days)
    created_at                TIMESTAMPTZ DEFAULT now(),
    updated_at                TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ticket_media (
    media_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id       UUID REFERENCES tickets(ticket_id),
    s3_key          TEXT NOT NULL,
    phash           BIT(64) NOT NULL,       -- perceptual hash, 64-bit DCT hash
    uploaded_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_media_phash ON ticket_media USING gin (phash);

-- Fuzzy criteria scores per ticket (TFN: lower, modal, upper)
CREATE TABLE ticket_criteria_scores (
    ticket_id       UUID REFERENCES tickets(ticket_id),
    criterion_code  TEXT NOT NULL,   -- C1_infra, C2_safety, C3_equity, C4_cost
    tfn_lower       NUMERIC(6,3) NOT NULL,
    tfn_modal       NUMERIC(6,3) NOT NULL,
    tfn_upper       NUMERIC(6,3) NOT NULL,
    source          TEXT,            -- 'citizen_report','field_scout','sensor'
    confidence      NUMERIC(4,3),    -- narrows over time as scout verifies
    updated_at      TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (ticket_id, criterion_code)
);

-- AHP criteria weights (versioned; expert pairwise comparisons)
CREATE TABLE criteria_weights (
    version_id      INT NOT NULL,
    criterion_code  TEXT NOT NULL,
    weight_lower    NUMERIC(5,4),
    weight_modal    NUMERIC(5,4),
    weight_upper    NUMERIC(5,4),
    consistency_ratio NUMERIC(5,4),   -- AHP CR, must be < 0.10
    effective_from  TIMESTAMPTZ,
    PRIMARY KEY (version_id, criterion_code)
);

-- TOPSIS output
CREATE TABLE ticket_scores (
    ticket_id       UUID REFERENCES tickets(ticket_id),
    cci_score       NUMERIC(6,5),     -- Closeness Coefficient, 0..1
    computed_at     TIMESTAMPTZ DEFAULT now(),
    weights_version INT,
    PRIMARY KEY (ticket_id, computed_at)
);

-- Daily dispatch manifest (Knapsack output)
CREATE TABLE dispatch_manifests (
    manifest_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispatch_date   DATE NOT NULL,
    budget_cap      NUMERIC(12,2),
    workforce_cap_hours NUMERIC(8,2),
    solver_status   TEXT,             -- OPTIMAL, FEASIBLE, INFEASIBLE
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE dispatch_manifest_items (
    manifest_id     UUID REFERENCES dispatch_manifests(manifest_id),
    ticket_id       UUID REFERENCES tickets(ticket_id),
    selected        BOOLEAN NOT NULL,
    cost_estimate   NUMERIC(10,2),
    hours_estimate  NUMERIC(6,2),
    PRIMARY KEY (manifest_id, ticket_id)
);

-- SHAP explanations, one row per ticket per manifest decision
CREATE TABLE ticket_explanations (
    explanation_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id       UUID REFERENCES tickets(ticket_id),
    manifest_id     UUID REFERENCES dispatch_manifests(manifest_id),
    shap_json        JSONB NOT NULL,   -- {criterion_code: shap_value, ...}
    nlg_message      TEXT NOT NULL,     -- final citizen-facing WhatsApp text
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- Immutable, hash-chained audit log for RTS defense
CREATE TABLE audit_log (
    log_id          BIGSERIAL PRIMARY KEY,
    entity_type     TEXT NOT NULL,   -- ticket, manifest, weights, message
    entity_id       UUID NOT NULL,
    action          TEXT NOT NULL,
    payload_json     JSONB NOT NULL,
    prev_hash        CHAR(64),
    this_hash         CHAR(64) NOT NULL,  -- SHA-256(prev_hash || payload_json)
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- Notification delivery log (WhatsApp)
CREATE TABLE notifications (
    notification_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id         UUID REFERENCES tickets(ticket_id),
    citizen_id          UUID REFERENCES citizens(citizen_id),
    template_name       TEXT,
    category               TEXT,  -- utility, authentication
    status                   TEXT,  -- queued, sent, delivered, read, failed
    wa_message_id          TEXT,
    cost_inr                 NUMERIC(6,2),
    sent_at                   TIMESTAMPTZ
);
```

### 3.2 Design notes

- **PostGIS** is required from day one: dedup radius queries, ward equity lookups, and the "high-traffic hospital route" example in Scenario B all depend on spatial joins.
- **TFN storage as three columns** (lower/modal/upper) rather than a single float is what makes the "incomplete data" fuzzy logic real — not just narrative. `confidence` narrows the interval as field scouts verify, which is the literal mechanism behind "fuzzy bounds tighten."
- **`audit_log` is hash-chained** (each row hashes in the previous row's hash) so a tampering attempt breaks the chain — this is the concrete implementation of "cryptographic logs" referenced in the RTS Defense Architecture section of the source report.

---

## 4. Module-by-Module Build Spec

### 4.1 Ingestion & Deduplication Service

**Stack:** Python 3.12, FastAPI, Celery + Redis (async media processing), `imagehash` + `Pillow`, boto3 (S3-compatible object storage — MinIO for on-prem, or a cheap Indian cloud bucket).

**Perceptual hash + Hamming-distance dedup (implements Phase 1 of source report):**

```python
from PIL import Image
import imagehash
from shapely.geometry import Point
from geoalchemy2.shape import to_shape

DEDUPE_HAMMING_THRESHOLD = 8      # tune empirically; 0-10 = likely same scene
DEDUPE_RADIUS_METERS = 150

def compute_phash(image_path: str) -> imagehash.ImageHash:
    img = Image.open(image_path).convert("L")   # grayscale
    return imagehash.phash(img, hash_size=8)      # 64-bit DCT-based hash

def find_duplicate_ticket(new_hash: imagehash.ImageHash,
                           new_location: Point,
                           db_session) -> str | None:
    """
    Returns parent_ticket_id if a near-duplicate open ticket exists
    within DEDUPE_RADIUS_METERS, else None.
    """
    candidates = db_session.execute(
        """
        SELECT t.ticket_id, m.phash
        FROM tickets t
        JOIN ticket_media m ON m.ticket_id = t.ticket_id
        WHERE t.status IN ('open','scored')
          AND ST_DWithin(t.location::geography, ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography, :radius)
        """,
        {"lng": new_location.x, "lat": new_location.y, "radius": DEDUPE_RADIUS_METERS},
    ).fetchall()

    for ticket_id, stored_hash_bits in candidates:
        stored_hash = imagehash.hex_to_hash(stored_hash_bits)
        if (new_hash - stored_hash) <= DEDUPE_HAMMING_THRESHOLD:   # Hamming distance
            return ticket_id
    return None

def ingest_ticket(payload, db_session):
    if payload.image_path:
        phash = compute_phash(payload.image_path)
        parent = find_duplicate_ticket(phash, payload.location, db_session)
        if parent:
            # attach as corroborating evidence, bump community multiplier
            db_session.execute(
                "UPDATE tickets SET community_multiplier = LEAST(community_multiplier + 0.15, 3.0) "
                "WHERE ticket_id = :pid", {"pid": parent}
            )
            attach_media(parent, payload, phash, db_session)
            return {"status": "deduped", "parent_ticket_id": parent}

    ticket_id = create_new_ticket(payload, db_session)
    if payload.image_path:
        attach_media(ticket_id, payload, phash, db_session)
    return {"status": "created", "ticket_id": ticket_id}
```

**Notes:**
- `hash_size=8` → 64-bit hash, matching the "binary hash" described in the source report's DCT explanation.
- Threshold (8) and radius (150 m) are **starting defaults** — must be calibrated during Phase 0 with a labeled sample of real duplicate/non-duplicate photo pairs from past Kopargaon monsoon events (see §7.2).

### 4.2 Fuzzy AHP — Criteria Weighting

Run **offline**, periodically (e.g., quarterly, or after a major incident prompts re-weighting), by a small panel of municipal domain experts (Chief Officer, ward engineers, sanitation head) completing pairwise comparisons in a lightweight web form.

```python
import numpy as np

def fuzzy_ahp_weights(pairwise_tfn_matrix: np.ndarray) -> dict:
    """
    pairwise_tfn_matrix: shape (n, n, 3) — each cell is a TFN (l, m, u)
    expressing "criterion i is how much more important than criterion j".
    Returns normalized fuzzy weight vector per criterion + consistency ratio.
    """
    n = pairwise_tfn_matrix.shape[0]

    # Geometric mean of each row (Buckley's method), per TFN component
    row_geo_means = np.zeros((n, 3))
    for i in range(n):
        row_geo_means[i] = np.prod(pairwise_tfn_matrix[i], axis=0) ** (1 / n)

    total = row_geo_means.sum(axis=0)          # sum across criteria, per TFN component
    weights = row_geo_means / total[::-1]       # normalize (l/u_sum, m/m_sum, u/l_sum)

    # Consistency check on the defuzzified (modal-value) crisp matrix
    crisp_matrix = pairwise_tfn_matrix[:, :, 1]
    consistency_ratio = compute_ahp_consistency_ratio(crisp_matrix)

    return {
        "weights": weights,          # array of (l, m, u) per criterion
        "consistency_ratio": consistency_ratio,
    }

def compute_ahp_consistency_ratio(crisp_matrix: np.ndarray) -> float:
    n = crisp_matrix.shape[0]
    eigvals = np.linalg.eigvals(crisp_matrix)
    lambda_max = np.max(eigvals.real)
    ci = (lambda_max - n) / (n - 1)
    ri_table = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24}
    ri = ri_table.get(n, 1.24)
    return ci / ri if ri else 0.0
```

- **Gate condition:** if `consistency_ratio >= 0.10`, the UI must reject the expert's pairwise comparisons and prompt them to redo the inconsistent judgments — this is a standard AHP validity rule and must not be skipped, or downstream weights become meaningless.
- Weights are versioned (`criteria_weights.version_id`) so every historical score can be traced to the weight set active when it was computed — required for RTS audit defense.

### 4.3 Fuzzy TOPSIS — Ticket Scoring

```python
import numpy as np

def normalize_tfn(tfn, col_type, col_extreme):
    l, m, u = tfn
    if col_type == "benefit":
        u_star = col_extreme  # max upper across all alternatives for this criterion
        return (l / u_star, m / u_star, u / u_star)
    else:  # cost criterion
        l_minus = col_extreme  # min lower across all alternatives for this criterion
        return (l_minus / u, l_minus / m, l_minus / l)

def tfn_vertex_distance(a, b):
    # Vertex method distance between two TFNs
    return np.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / 3)

def fuzzy_topsis(decision_matrix: dict, weights: dict, criteria_types: dict):
    """
    decision_matrix: {ticket_id: {criterion: (l,m,u)}}
    weights:          {criterion: (l,m,u)}   — from fuzzy_ahp_weights()
    criteria_types:   {criterion: 'benefit' | 'cost'}
    Returns {ticket_id: closeness_coefficient}
    """
    criteria = list(weights.keys())

    # Step 1: normalize
    extremes = {}
    for c in criteria:
        vals = [decision_matrix[t][c] for t in decision_matrix]
        extremes[c] = max(v[2] for v in vals) if criteria_types[c] == "benefit" \
                      else min(v[0] for v in vals)

    normalized = {
        t: {c: normalize_tfn(decision_matrix[t][c], criteria_types[c], extremes[c])
            for c in criteria}
        for t in decision_matrix
    }

    # Step 2: weighted normalized matrix
    weighted = {
        t: {c: tuple(normalized[t][c][i] * weights[c][i] for i in range(3))
            for c in criteria}
        for t in normalized
    }

    # Step 3: FPIS / FNIS (component-wise max/min over l,m,u, per axiom of the method)
    fpis = {c: (1, 1, 1) for c in criteria}   # weighted-normalized values are bounded in [0,1]
    fnis = {c: (0, 0, 0) for c in criteria}

    # Step 4: separation measures
    d_plus, d_minus = {}, {}
    for t in weighted:
        d_plus[t] = sum(tfn_vertex_distance(weighted[t][c], fpis[c]) for c in criteria)
        d_minus[t] = sum(tfn_vertex_distance(weighted[t][c], fnis[c]) for c in criteria)

    # Step 5: closeness coefficient
    cci = {t: d_minus[t] / (d_plus[t] + d_minus[t]) if (d_plus[t] + d_minus[t]) > 0 else 0
           for t in weighted}

    return cci
```

**Runtime pattern:** run as a scheduled job (every 15–30 minutes, or on-demand when a ticket's evidence changes) over all `status IN ('open','scored')` tickets. Each run writes a new row into `ticket_scores` (append, not overwrite) so score history is preserved for audit.

### 4.4 Knapsack Optimizer — Daily Dispatch (RCPSP as multi-dimensional 0-1 knapsack)

**Stack:** Google OR-Tools (`CP-SAT` solver) — free, fast, and handles integer/binary constraints natively (better fit than a hand-rolled DP for multi-dimensional constraints).

```python
from ortools.sat.python import cp_model

def optimize_daily_dispatch(tickets: list[dict], budget_cap: float, hours_cap: float):
    """
    tickets: [{'ticket_id', 'cci_score', 'cost', 'hours'}]
    Solves: maximize sum(cci_score_i * x_i)
            subject to sum(cost_i * x_i) <= budget_cap
                       sum(hours_i * x_i) <= hours_cap
                       x_i in {0,1}
    """
    model = cp_model.CpModel()
    x = {t["ticket_id"]: model.NewBoolVar(t["ticket_id"]) for t in tickets}

    # Scale to integers (CP-SAT requires integer coefficients)
    SCALE = 1000
    model.Add(
        sum(int(t["cost"] * SCALE) * x[t["ticket_id"]] for t in tickets)
        <= int(budget_cap * SCALE)
    )
    model.Add(
        sum(int(t["hours"] * SCALE) * x[t["ticket_id"]] for t in tickets)
        <= int(hours_cap * SCALE)
    )
    model.Maximize(
        sum(int(t["cci_score"] * SCALE) * x[t["ticket_id"]] for t in tickets)
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    status = solver.Solve(model)

    selected = [t["ticket_id"] for t in tickets if solver.Value(x[t["ticket_id"]]) == 1]
    return {
        "status": solver.StatusName(status),
        "selected_ticket_ids": selected,
        "objective_value": solver.ObjectiveValue() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
    }
```

**Extensions to plan for (v2):**
- Add a third dimension (e.g., specialized-crew availability: only 1 crane truck) as an additional constraint row — CP-SAT scales to this trivially.
- Add a **soft SLA-breach penalty term** in the objective so tickets nearing their 21–45 day RTS deadline get an automatic urgency boost even if their raw CCi is mid-tier — prevents "perpetually deferred" tickets.

### 4.5 Explainability Service (SHAP)

Because CCi is computed via a **transparent closed-form formula** (not a black-box ML model), SHAP is applied in one of two ways depending on scale:

- **Preferred (cheap, exact given TOPSIS's additive-like structure):** compute a **feature-contribution decomposition** directly from the weighted-normalized distances (`d_plus`, `d_minus` per criterion) rather than running a generic SHAP estimator — this gives an *exact*, not approximated, per-criterion attribution, and is far cheaper at municipal scale (thousands of tickets/month).
- **If/when a learned model is introduced** (e.g., an ML risk-severity predictor trained on historical resolution outcomes), use `shap.TreeExplainer` (if tree-based) or `shap.KernelExplainer` (model-agnostic) on that specific sub-model only.

```python
def exact_topsis_shap(ticket_id, weighted_matrix, fpis, fnis, criteria):
    """
    Exact per-criterion contribution to (1 - CCi) "distance from ideal" —
    reported as a SHAP-style attribution vector for NLG translation.
    """
    contributions = {}
    total_d_plus = sum(tfn_vertex_distance(weighted_matrix[ticket_id][c], fpis[c]) for c in criteria)
    for c in criteria:
        d_c = tfn_vertex_distance(weighted_matrix[ticket_id][c], fpis[c])
        # Negative sign: larger distance from ideal = negative contribution to priority
        contributions[c] = -(d_c / total_d_plus) if total_d_plus > 0 else 0
    return contributions
```

**NLG templater** (rule-based, not generative — for auditability and cost control):

```python
NLG_TEMPLATES = {
    "high_safety_infra": "Your request has been prioritized for immediate action due to high risks to public safety and critical infrastructure. Teams are deployed.",
    "high_cost_deferred": "Your request is verified. Due to high resource requirements, it has been scheduled for the next budget cycle window.",
    "equity_priority": "Your request has been approved. We are actively prioritizing service balancing in your ward to ensure equal civic maintenance.",
    "deferred_higher_priority": "Your report of {category} is logged. Due to a higher-priority emergency requiring resource deployment ({reason}), your case is deferred by approximately {delay_estimate}. Thank you for your patience.",
}

def generate_nlg_message(ticket, shap_contributions, decision):
    dominant_criterion = max(shap_contributions, key=lambda c: abs(shap_contributions[c]))
    if decision == "dispatched" and dominant_criterion in ("C1_infra", "C2_safety"):
        return NLG_TEMPLATES["high_safety_infra"]
    if decision == "deferred" and dominant_criterion == "C4_cost":
        return NLG_TEMPLATES["high_cost_deferred"]
    if decision == "dispatched" and dominant_criterion == "C3_equity":
        return NLG_TEMPLATES["equity_priority"]
    if decision == "deferred":
        return NLG_TEMPLATES["deferred_higher_priority"].format(
            category=ticket["category"], reason="a higher-severity incident", delay_estimate="24 hours"
        )
    return "Your request status has been updated. Reply HELP for details."
```

### 4.6 WhatsApp Notification Service

**Stack:** Meta WhatsApp Business Cloud API (direct, or via a BSP like Gupshup/Interakt for India-specific onboarding support), a message queue (Redis/RabbitMQ) for retry-safe delivery, template pre-approval workflow.

Key implementation requirements:
- All citizen-facing messages must use **pre-approved Utility Message templates** (Meta requires template approval before send for messages outside the 24-hour session window).
- **Template categories to register:** `ticket_submitted`, `ticket_prioritized`, `ticket_deferred_reason`, `ticket_resolved`, `otp_verification`.
- Delivery status webhooks (`sent`/`delivered`/`read`/`failed`) must write back to `notifications.status` for cost tracking and appeal-defense completeness.
- Retry policy: 3 attempts with exponential backoff; permanent failures fall back to SMS (cheap gateway) as a secondary channel for citizens without WhatsApp.

```python
import httpx

WA_API_URL = "https://graph.facebook.com/v20.0/{phone_number_id}/messages"

async def send_utility_message(to_number: str, template_name: str, params: list[str], phone_number_id: str, token: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},   # add "mr" (Marathi) template variants too
            "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            WA_API_URL.format(phone_number_id=phone_number_id),
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
```

**Important, non-obvious requirement:** all citizen-facing copy must ship in **Marathi** (and ideally Hindi) as the primary language, with English as fallback — the source report's example messages are in English for illustration, but Kopargaon's population is predominantly Marathi-speaking. Register bilingual templates from day one.

### 4.7 Admin / Chief Officer Dashboard

**Stack:** React + TypeScript, TailwindCSS, a mapping library (MapLibre GL JS + PostGIS tiles via `pg_tileserv` or Mapbox), charting (Recharts).

Core screens:
1. **Live Ward Map** — heat-colored by open-ticket CCi score, clustered pins.
2. **Daily Dispatch Manifest** — the Knapsack solver's output, editable by the Chief Officer with a manual-override audit trail (any override is itself logged and must carry a justification string).
3. **SLA Risk Board** — tickets sorted by days-to-RTS-deadline, filterable.
4. **Weight Calibration Panel** — the AHP pairwise-comparison UI for periodic re-weighting, with the CR-gate validation from §4.2.
5. **Audit Export** — one-click export of the hash-chained log for a given ticket/date range, formatted for RTS appeal submission.

---

## 5. API Contract (representative endpoints)

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `POST` | `/v1/tickets` | Citizen submits a new grievance (web/app) | Citizen JWT / OTP |
| `POST` | `/v1/webhooks/whatsapp` | Inbound WhatsApp messages/media | Meta signature verification |
| `GET` | `/v1/tickets/{id}` | Ticket detail incl. current CCi score | Staff/Citizen (scoped) |
| `GET` | `/v1/manifests/{date}` | Daily dispatch manifest | Staff (ward-scoped RBAC) |
| `POST` | `/v1/manifests/{date}/override` | Manual override with justification | Chief Officer role only |
| `GET` | `/v1/tickets/{id}/explanation` | SHAP + NLG explanation | Staff/Citizen (scoped) |
| `GET` | `/v1/audit/export` | Hash-chained audit export (date/ticket range) | Chief Officer / Legal role |
| `POST` | `/v1/weights/calibrate` | Submit AHP pairwise comparisons | Domain-expert role |
| `GET` | `/v1/wards/{id}/stats` | Ward-level dashboard aggregates | Staff |

All endpoints versioned (`/v1/`), OpenAPI 3.1 spec generated from FastAPI automatically, rate-limited at the gateway.

---

## 6. Infrastructure, Security & Compliance

### 6.1 Deployment target

Given Kopargaon's scale (~65,000 population, likely modest IT budget), avoid over-engineering:

- **Compute:** a single small Kubernetes cluster (3 nodes) or, more pragmatically for year 1, a **managed container platform** (e.g., a 2–4 vCPU / 8–16 GB VM pair with Docker Compose + a managed Postgres) is sufficient. Kubernetes only pays off once traffic/complexity grows — recommend starting simpler.
- **Hosting:** an Indian data-center region of a major cloud provider, or empanelled NIC/MeitY cloud infrastructure if the municipality is required to use government-empanelled hosting (common for ULBs — confirm with the district IT cell before architecture lock-in).
- **Object storage:** S3-compatible bucket (or MinIO self-hosted) for grievance photos, lifecycle-policy to archive resolved-ticket media after 12 months.
- **Database:** managed PostgreSQL + PostGIS extension; daily automated backups, point-in-time recovery enabled (this is the system of record for RTS legal defense — backups are non-negotiable).

### 6.2 Security

- OTP-based citizen authentication (phone number as identity) — no password storage needed for citizens.
- Staff/admin auth via short-lived JWTs + refresh tokens; ward-level RBAC (a ward engineer sees only their ward's tickets; Chief Officer sees all).
- All PII (phone numbers) encrypted at rest (`pgcrypto` column-level encryption or full-disk encryption at minimum).
- WhatsApp webhook signature verification (Meta's `X-Hub-Signature-256`) mandatory to reject spoofed inbound payloads.
- Media uploads virus-scanned before persisting (ClamAV in the ingestion pipeline) — grievance photo uploads are a public-facing attack surface.

### 6.3 RTS Audit-Defense Design (concrete mechanism)

The source report requires the system to produce "cryptographic logs" proving delays were resource-driven, not negligent. Concretely:

```python
import hashlib, json

def append_audit_log(entity_type, entity_id, action, payload: dict, prev_hash: str, db_session):
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    this_hash = hashlib.sha256((prev_hash or "") .encode() + payload_str.encode()).hexdigest()
    db_session.execute(
        "INSERT INTO audit_log (entity_type, entity_id, action, payload_json, prev_hash, this_hash) "
        "VALUES (:et, :eid, :act, :pl, :ph, :th)",
        {"et": entity_type, "eid": entity_id, "act": action, "pl": payload_str, "ph": prev_hash, "th": this_hash},
    )
    return this_hash
```

Every write to `tickets`, `dispatch_manifest_items`, `criteria_weights`, and `notifications` triggers an `append_audit_log` call. A verification job periodically re-walks the chain and alerts if any `this_hash` no longer matches its recomputed value — proving tamper-evidence, which is the actual legal value (not "cryptographic" in the sense of encryption, but in the sense of a verifiable hash chain, similar in spirit to a blockchain but without needing a distributed ledger).

---

## 7. Testing & Validation Strategy

### 7.1 Unit / component tests
- Fuzzy AHP: verify known pairwise-comparison matrices reproduce published textbook weight vectors and consistency ratios.
- Fuzzy TOPSIS: verify CCi ∈ [0,1], and that an alternative dominating all benefit criteria and minimizing all cost criteria scores CCi → 1.
- Knapsack solver: verify constraint satisfaction (`sum(cost) <= budget`, `sum(hours) <= hours_cap`) on generated test instances, including edge cases (zero budget, single feasible ticket, infeasible over-budget set).
- pHash dedup: build a labeled test set of ~200 photo pairs (same-scene vs. different-scene) from archived Kopargaon monsoon reports if available, or a public duplicate-image benchmark, to tune `DEDUPE_HAMMING_THRESHOLD` and measure precision/recall before go-live.

### 7.2 Calibration with domain experts
- Run at least 2 AHP pairwise-comparison workshops with Chief Officer + ward engineers + sanitation head before go-live; require CR < 0.10 on all resulting matrices.
- Backtest the MCDA + Knapsack pipeline against **3–5 historical real incidents** (e.g., a past monsoon event, if records exist) to sanity-check that the system's recommended dispatch would have matched (or improved on) what actually happened.

### 7.3 Load & resilience testing
- Simulate the "500 tickets after a storm" scenario from the source report: burst-load test ingestion + dedup pipeline at 10x expected peak throughput.
- Chaos-test the WhatsApp notification queue (API downtime, rate-limit responses) to confirm retry/backoff behaves correctly and doesn't drop citizen-facing messages silently.

### 7.4 UAT with real users
- Pilot in **2–3 wards only** for one full monsoon cycle before municipality-wide rollout (see Phase 4 in roadmap).
- Collect citizen feedback on WhatsApp message clarity (via a simple 1–5 satisfaction reply prompt) and staff feedback on dashboard usability.

---

## 8. Phased Delivery Roadmap

| Phase | Duration | Scope | Exit Criteria |
|---|---|---|---|
| **Phase 0 — Discovery & Calibration** | 3 weeks | Confirm hosting constraints (govt-empanelled cloud?), collect historical ticket data if available, run first AHP workshop, define criteria + SLA mapping per RTS category, finalize ward boundary GIS data | Signed-off criteria set, CR < 0.10 weight matrix, ward geometries loaded |
| **Phase 1 — Core Data Layer & Ingestion** | 4 weeks | DB schema, citizen submission API (web form first), pHash dedup service, media storage, basic ward map | Citizens can submit tickets; duplicates auto-merge with >85% precision on test set |
| **Phase 2 — MCDA & Optimization Engine** | 5 weeks | Fuzzy AHP weight service, Fuzzy TOPSIS scoring job, OR-Tools Knapsack optimizer, daily manifest generation | Manifest generated nightly; backtested against 3 historical scenarios with plausible results |
| **Phase 3 — Explainability & WhatsApp Loop** | 4 weeks | SHAP/exact-attribution service, NLG templates (English + Marathi), WhatsApp Cloud API integration, template approval with Meta | Every dispatched/deferred ticket triggers a correct, bilingual WhatsApp message within 5 minutes |
| **Phase 4 — Admin Dashboard & RBAC** | 4 weeks | React dashboard (map, manifest view, override flow, audit export), auth/RBAC | Chief Officer can view, override (with justification), and export audit logs end-to-end |
| **Phase 5 — Pilot (2–3 wards)** | 8 weeks (spans monsoon window if possible) | Live pilot, daily monitoring, weekly retros with municipal staff | Positive staff/citizen feedback, no critical incidents, dedup precision/recall confirmed on real data |
| **Phase 6 — Municipality-wide Rollout & Hardening** | 4 weeks | Full ward rollout, load testing at scale, backup/DR drill, staff training | All wards live; DR restore tested; training completed for all relevant staff |

**Total indicative timeline: ~32 weeks (~7.5 months)** from kickoff to full rollout, assuming a small dedicated team and no major procurement delays (government procurement/tendering timelines are the biggest real-world risk to this schedule — see Risk Register).

---

## 9. Team & Indicative Cost (India-market, ballpark)

| Role | Allocation | Notes |
|---|---|---|
| Tech Lead / Architect | 1, full-time | Owns architecture, code review, OR-Tools + Fuzzy MCDA correctness |
| Backend Engineer (Python) | 2, full-time | Ingestion, MCDA, Knapsack, WhatsApp integration |
| Frontend Engineer (React) | 1, full-time | Admin dashboard, citizen web form |
| Data/GIS Engineer | 1, part-time | PostGIS, ward geometry, spatial dedup tuning |
| QA/Test Engineer | 1, part-time from Phase 2 | Test suites, calibration backtesting |
| DevOps | 1, part-time | Infra, CI/CD, backups, monitoring |
| Domain Liaison (Municipal) | Chief Officer's office, part-time | AHP workshops, ward validation, RTS mapping |
| UX/Content (Marathi copy) | Contract, Phase 3 | Bilingual NLG templates, citizen-facing copy review |

A 6–7 person core team over ~7.5 months is a realistic staffing shape for a project of this scope; exact INR budgeting depends on in-house vs. vendor sourcing and government empanelment requirements, which should be confirmed with the district IT cell before finalizing procurement.

Recurring operating cost (post-launch), from the source report's own estimate: **~₹720/month** in WhatsApp utility messaging at 1,500 tickets/month, plus **₹1,500–₹3,000/month** BSP platform fee, plus standard cloud hosting (small managed Postgres + 2–4 vCPU compute is typically a few thousand INR/month on Indian cloud regions) — total recurring cost is modest relative to typical ULB IT budgets.

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Government procurement/tendering delays push timeline | High | High | Start Phase 0 discovery in parallel with procurement process; design for vendor-neutral, empanelled-cloud compatibility from day one |
| AHP expert panel produces inconsistent weights (CR ≥ 0.10) repeatedly | Medium | Medium | Build the CR-gate UI early (Phase 0/2); run practice workshops before the "official" calibration |
| Low WhatsApp adoption among elderly/rural citizens | Medium | Medium | SMS fallback channel; retain the existing web/Aaple Sarkar submission path as parallel input |
| Perceptual-hash dedup false-merges genuinely distinct nearby issues | Medium | High (citizen trust) | Conservative threshold at launch (favor under-merging), field-scout confirmation step before permanent merge, easy "these are different issues" staff override |
| Field data (GPS, ward boundaries) inaccurate or incomplete | Medium | Medium | Dedicated GIS validation pass in Phase 0; allow manual ward correction in ticket intake |
| Meta WhatsApp template approval delays | Low–Medium | Medium | Submit template approvals in Phase 2, not Phase 3, to buffer Meta's review turnaround |
| Perception of "algorithmic unfairness" by citizens/press | Medium | High (political) | SHAP-driven transparent explanations (already designed in), plus a public-facing plain-language explainer page describing the methodology |
| Data privacy concerns (phone numbers, photos of private property) | Medium | High | Encryption at rest, minimal PII retention policy, media auto-purge after resolution + retention window, published privacy notice |

---

## 11. Immediate Next Steps

1. Confirm hosting constraints with the district/state IT cell (empanelled cloud vs. open choice) — this affects the entire infra section and should be resolved before Phase 1 starts.
2. Schedule the first Fuzzy AHP calibration workshop with the Chief Officer's office and ward engineers (Phase 0).
3. Identify and export any existing historical grievance data (from Aaple Sarkar or manual ledgers) for backtesting — even a partial dataset materially de-risks Phase 2.
4. Begin Meta WhatsApp Business API + BSP onboarding paperwork in parallel, since business verification can take several weeks independent of engineering progress.
