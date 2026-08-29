"""
sqlite3 data layer for the Kopargaon CRPP backend.

Why stdlib sqlite3 instead of an ORM: the project venv has no SQLAlchemy, and
this module needs to be importable and exercisable with a bare Python install.
All SQL lives in this module, so moving to Postgres/Supabase later means
rewriting one file rather than the application.

Everything here is idempotent: init_db() can be called on every startup.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from config import settings
except ImportError:  # pragma: no cover - allows `import backend.database`
    from backend.config import settings


# ---------------------------------------------------------------------------
# small shared helpers
# ---------------------------------------------------------------------------

def new_id() -> str:
    """UUID4 string. Used for every primary key so ids stay portable to
    Postgres ``uuid`` columns without a rewrite."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def civic_tz() -> timezone | ZoneInfo:
    """The council's timezone, or UTC if the host has no zone database.

    Falling back is deliberate: a missing tzdata should degrade the labelling of
    a date, not stop the service from booting.
    """
    try:
        return ZoneInfo(settings.CIVIC_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def civic_now(when: str | datetime | None = None) -> datetime:
    """An instant expressed in the council's own timezone."""
    if isinstance(when, datetime):
        moment = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
    elif isinstance(when, str):
        moment = parse_iso(when) or utcnow()
    else:
        moment = utcnow()
    return moment.astimezone(civic_tz())


def civic_date(when: str | datetime | None = None) -> str:
    """The calendar date as Kopargaon sees it, ``YYYY-MM-DD``.

    Timestamps are stored in UTC because an instant has no opinion about where
    it happened. A *date*, though, is a civic fact: "today's dispatch" means the
    day the officer is standing in. Between midnight and 05:30 IST the UTC date
    is still yesterday, so deriving dates from UTC would file a 3 a.m. run --
    and the reference number printed on the citizen's receipt -- under the wrong
    day.
    """
    return civic_now(when).date().isoformat()


def utcnow_iso() -> str:
    """ISO-8601 UTC with a trailing 'Z'. Stored as TEXT because sqlite has no
    native timestamp type; lexicographic ordering still matches chronological."""
    return utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def dumps(value: Any) -> str | None:
    """JSON column writer. None stays None so 'unknown' is never '[]' or '{}'."""
    return None if value is None else json.dumps(value, ensure_ascii=False)


def loads(value: Any, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# connection handling
# ---------------------------------------------------------------------------

def connect() -> sqlite3.Connection:
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(settings.DB_PATH),
        timeout=30.0,
        isolation_level=None,          # explicit transactions, see transaction()
        check_same_thread=False,       # FastAPI runs handlers on a threadpool
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL is the right default on a local disk, but it needs shared-memory
    # mapping that network/virtualised mounts sometimes refuse. Fall back rather
    # than refuse to start.
    for mode in (settings.SQLITE_JOURNAL_MODE, "DELETE"):
        try:
            conn.execute(f"PRAGMA journal_mode = {mode}")
            conn.execute("PRAGMA user_version").fetchone()
            break
        except sqlite3.Error:
            continue
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    if settings.SQL_ECHO:
        conn.set_trace_callback(lambda s: print("[sql]", " ".join(s.split())))
    return conn


@contextmanager
def get_conn():
    """Short-lived connection. Use for reads or for a single self-contained
    unit of work."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection | None = None):
    """Explicit transaction. Rolls back on any exception.

    Triage and ticket ingestion both write several tables plus an audit row;
    they must be all-or-nothing or the audit chain stops matching reality.
    """
    own = conn is None
    conn = conn or connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        if own:
            conn.close()


def get_db():
    """FastAPI dependency: ``conn: sqlite3.Connection = Depends(get_db)``."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def query_all(conn: sqlite3.Connection, sql: str,
              params: Sequence[Any] | dict = ()) -> list[sqlite3.Row]:
    return conn.execute(sql, params).fetchall()


def query_one(conn: sqlite3.Connection, sql: str,
              params: Sequence[Any] | dict = ()) -> sqlite3.Row | None:
    return conn.execute(sql, params).fetchone()


def execute(conn: sqlite3.Connection, sql: str,
            params: Sequence[Any] | dict = ()) -> sqlite3.Cursor:
    return conn.execute(sql, params)


def executemany(conn: sqlite3.Connection, sql: str,
                seq: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
    return conn.executemany(sql, list(seq))


def insert(conn: sqlite3.Connection, table: str, row: dict) -> str | int:
    """Parameterised INSERT built from dict keys. Keys are validated against a
    conservative identifier pattern so a caller can never inject SQL through a
    column name."""
    cols = list(row.keys())
    for col in cols:
        if not col.replace("_", "").isalnum():
            raise ValueError(f"illegal column name: {col!r}")
    placeholders = ", ".join("?" for _ in cols)
    sql = (f"INSERT INTO {table} ({', '.join(cols)}) "
           f"VALUES ({placeholders})")
    cur = conn.execute(sql, [row[c] for c in cols])
    return row.get("id", cur.lastrowid)


def update(conn: sqlite3.Connection, table: str, row_id: str,
           changes: dict) -> None:
    if not changes:
        return
    for col in changes:
        if not col.replace("_", "").isalnum():
            raise ValueError(f"illegal column name: {col!r}")
    sets = ", ".join(f"{c} = ?" for c in changes)
    conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?",
                 [*changes.values(), row_id])


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return None if row is None else {k: row[k] for k in row.keys()}


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------
# Conventions:
#   * ids are TEXT uuid4
#   * timestamps are TEXT ISO-8601 UTC ('...Z')
#   * NULL means "unknown / not verified" and is never substituted with 0.
#     The Kopargaon datasets are explicit that unknown quantities and costs must
#     stay null and be flagged, so the schema enforces that distinction with
#     companion *_confidence / *_status columns.

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wards (
    id                TEXT PRIMARY KEY,
    ward_no           TEXT,
    name              TEXT NOT NULL,
    population        INTEGER,
    households        INTEGER,
    area_sq_km        REAL,
    centroid_lat      REAL,
    centroid_lon      REAL,
    equity_index      REAL,
    flood_exposure    TEXT,
    data_confidence   TEXT NOT NULL DEFAULT 'unverified',
    source_note       TEXT,
    is_active         INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_wards_ward_no ON wards(ward_no)
    WHERE ward_no IS NOT NULL;

CREATE TABLE IF NOT EXISTS citizens (
    id                 TEXT PRIMARY KEY,
    phone              TEXT NOT NULL UNIQUE,
    name               TEXT,
    preferred_language TEXT NOT NULL DEFAULT 'en',
    ward_id            TEXT REFERENCES wards(id),
    is_blocked         INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id             TEXT PRIMARY KEY,
    username       TEXT NOT NULL UNIQUE,
    full_name      TEXT,
    role           TEXT NOT NULL,
    department_id  TEXT,
    ward_scope     TEXT,
    password_hash  TEXT NOT NULL,
    is_active      INTEGER NOT NULL DEFAULT 1,
    last_login_at  TEXT,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS otp_codes (
    id          TEXT PRIMARY KEY,
    phone       TEXT NOT NULL,
    code_hash   TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    consumed_at TEXT,
    attempts    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_otp_phone ON otp_codes(phone, expires_at);

CREATE TABLE IF NOT EXISTS tickets (
    id                  TEXT PRIMARY KEY,
    ref_no              TEXT UNIQUE,
    citizen_id          TEXT REFERENCES citizens(id),
    citizen_phone       TEXT,
    channel             TEXT NOT NULL DEFAULT 'web',
    category            TEXT NOT NULL,
    description         TEXT,
    lat                 REAL,
    lon                 REAL,
    ward_id             TEXT REFERENCES wards(id),
    landmark            TEXT,
    sensitive_site      TEXT,
    affected_population INTEGER,
    duration_hours      REAL,
    -- Status vocabulary is the one the existing React dashboard already
    -- colour-codes, so the backend must not invent its own:
    -- open -> scored -> scheduled | deferred -> dispatched -> resolved,
    -- plus 'deduped' for a report folded into another ticket.
    status              TEXT NOT NULL DEFAULT 'open',
    priority_floor      TEXT,
    department_id       TEXT,
    assigned_team       TEXT,
    -- two clocks that must never be merged (see the SLA dataset):
    -- operational response target in minutes vs statutory RTS days.
    reported_at              TEXT NOT NULL,
    acknowledged_at          TEXT,
    operational_target_minutes REAL,
    operational_deadline_at  TEXT,
    is_statutory_rts         INTEGER NOT NULL DEFAULT 0,
    rts_service_id           TEXT,
    rts_time_limit_days      INTEGER,
    rts_deadline_at          TEXT,
    external_handoff         TEXT,
    -- deduplication / community weight
    is_duplicate         INTEGER NOT NULL DEFAULT 0,
    duplicate_of_id      TEXT REFERENCES tickets(id),
    recurrence_of_id     TEXT REFERENCES tickets(id),
    dedup_evidence       TEXT,
    community_multiplier REAL NOT NULL DEFAULT 1.0,
    report_count         INTEGER NOT NULL DEFAULT 1,
    -- operator-confirmable escalating conditions (drive C1/C2, never assumed)
    blocks_major_road          INTEGER NOT NULL DEFAULT 0,
    access_isolated            INTEGER NOT NULL DEFAULT 0,
    critical_facility_isolated INTEGER NOT NULL DEFAULT 0,
    -- cost: NULL cost with status COST_INCOMPLETE, never 0 for unknown
    estimated_cost_inr   REAL,
    cost_status          TEXT NOT NULL DEFAULT 'COST_INCOMPLETE',
    cost_confidence      TEXT,
    cost_breakdown       TEXT,
    cost_inputs          TEXT,
    estimated_hours      REAL,
    required_roles       TEXT,
    candidate_equipment  TEXT,
    -- criteria derivation summary (full detail in ticket_criteria_scores)
    criteria_flags       TEXT,
    overall_confidence   REAL,
    -- latest decision snapshot (history lives in ticket_scores)
    latest_cci        REAL,
    latest_rank       INTEGER,
    latest_weight_version INTEGER,
    escalation_level  INTEGER NOT NULL DEFAULT 0,
    escalated_at      TEXT,
    resolved_at       TEXT,
    closure_note      TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS ix_tickets_category ON tickets(category);
CREATE INDEX IF NOT EXISTS ix_tickets_ward ON tickets(ward_id);
CREATE INDEX IF NOT EXISTS ix_tickets_dup ON tickets(duplicate_of_id);
CREATE INDEX IF NOT EXISTS ix_tickets_reported ON tickets(reported_at);
CREATE INDEX IF NOT EXISTS ix_tickets_deadline ON tickets(operational_deadline_at);

CREATE TABLE IF NOT EXISTS ticket_media (
    id          TEXT PRIMARY KEY,
    ticket_id   TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    file_path   TEXT,
    media_type  TEXT NOT NULL DEFAULT 'image',
    phash       TEXT,
    phash_bits  INTEGER,
    width       INTEGER,
    height      INTEGER,
    size_bytes  INTEGER,
    captured_at TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_media_ticket ON ticket_media(ticket_id);
CREATE INDEX IF NOT EXISTS ix_media_phash ON ticket_media(phash);

-- One row per criterion per ticket. TFN stored as three columns plus a
-- confidence in [0,1] and the evidence that produced it, so any score can be
-- traced back to a fact rather than a vibe.
CREATE TABLE IF NOT EXISTS ticket_criteria_scores (
    id            TEXT PRIMARY KEY,
    ticket_id     TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    criterion     TEXT NOT NULL,
    tfn_lower     REAL NOT NULL,
    tfn_modal     REAL NOT NULL,
    tfn_upper     REAL NOT NULL,
    confidence    REAL NOT NULL DEFAULT 0.5,
    source        TEXT NOT NULL DEFAULT 'derived',
    evidence      TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE(ticket_id, criterion)
);

-- Versioned Fuzzy-AHP output. A version is only usable when
-- consistency_ratio < threshold; failed matrices are still stored (is_active=0)
-- because "we rejected this expert matrix for CR=0.14" is part of the defence.
CREATE TABLE IF NOT EXISTS criteria_weights (
    version           INTEGER PRIMARY KEY AUTOINCREMENT,
    label             TEXT,
    criteria          TEXT NOT NULL,
    criteria_types    TEXT NOT NULL,
    pairwise_matrix   TEXT,
    fuzzy_weights     TEXT NOT NULL,
    crisp_weights     TEXT NOT NULL,
    consistency_ratio REAL,
    cr_threshold      REAL,
    cr_passed         INTEGER NOT NULL DEFAULT 1,
    method            TEXT NOT NULL DEFAULT 'buckley_geometric_mean',
    is_active         INTEGER NOT NULL DEFAULT 0,
    created_by        TEXT,
    note              TEXT,
    created_at        TEXT NOT NULL
);

-- Append-only score history. Never UPDATEd: a citizen asking "why was my
-- complaint ranked 14th on 3 September" must get the number that was actually
-- used that day, not today's recomputation.
CREATE TABLE IF NOT EXISTS ticket_scores (
    id               TEXT PRIMARY KEY,
    ticket_id        TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    run_id           TEXT NOT NULL,
    weight_version   INTEGER,
    cci              REAL NOT NULL,
    cci_base         REAL,
    community_multiplier REAL,
    sla_bonus        REAL,
    rank_position    INTEGER,
    d_positive       REAL,
    d_negative       REAL,
    criteria_snapshot TEXT,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_scores_ticket ON ticket_scores(ticket_id);
CREATE INDEX IF NOT EXISTS ix_scores_run ON ticket_scores(run_id);

CREATE TABLE IF NOT EXISTS dispatch_manifests (
    id                  TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL UNIQUE,
    dispatch_date       TEXT NOT NULL,
    ward_id             TEXT REFERENCES wards(id),
    weight_version      INTEGER,
    budget_available    REAL,
    workforce_available REAL,
    budget_used         REAL,
    workforce_used      REAL,
    total_candidates    INTEGER NOT NULL DEFAULT 0,
    allocated_count     INTEGER NOT NULL DEFAULT 0,
    deferred_count      INTEGER NOT NULL DEFAULT 0,
    cost_incomplete_count INTEGER NOT NULL DEFAULT 0,
    solver              TEXT,
    objective_value     REAL,
    budget_outcome      TEXT,
    created_by          TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_manifest_date ON dispatch_manifests(dispatch_date);

CREATE TABLE IF NOT EXISTS dispatch_manifest_items (
    id             TEXT PRIMARY KEY,
    manifest_id    TEXT NOT NULL REFERENCES dispatch_manifests(id) ON DELETE CASCADE,
    ticket_id      TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    decision       TEXT NOT NULL,
    rank_position  INTEGER,
    cci            REAL,
    cost_inr       REAL,
    hours          REAL,
    cost_status    TEXT,
    department_id  TEXT,
    required_roles TEXT,
    reason_code    TEXT,
    reason_text    TEXT,
    created_at     TEXT NOT NULL,
    UNIQUE(manifest_id, ticket_id)
);
CREATE INDEX IF NOT EXISTS ix_items_ticket ON dispatch_manifest_items(ticket_id);

CREATE TABLE IF NOT EXISTS ticket_explanations (
    id                 TEXT PRIMARY KEY,
    ticket_id          TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    run_id             TEXT,
    method             TEXT NOT NULL,
    attribution        TEXT NOT NULL,
    top_driver         TEXT,
    decision           TEXT,
    citizen_message_en TEXT,
    citizen_message_mr TEXT,
    officer_rationale  TEXT,
    created_at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_expl_ticket ON ticket_explanations(ticket_id);

CREATE TABLE IF NOT EXISTS notifications (
    id           TEXT PRIMARY KEY,
    ticket_id    TEXT REFERENCES tickets(id) ON DELETE CASCADE,
    citizen_id   TEXT REFERENCES citizens(id),
    recipient    TEXT,
    event        TEXT NOT NULL,
    channel      TEXT NOT NULL DEFAULT 'whatsapp',
    language     TEXT NOT NULL DEFAULT 'en',
    body         TEXT,
    payload      TEXT,
    status       TEXT NOT NULL DEFAULT 'queued',
    provider_message_id TEXT,
    error        TEXT,
    attempts     INTEGER NOT NULL DEFAULT 0,
    queued_at    TEXT NOT NULL,
    sent_at      TEXT
);
CREATE INDEX IF NOT EXISTS ix_notif_status ON notifications(status, queued_at);

-- Hash-chained append-only audit trail. seq is monotonic; entry_hash =
-- sha256(prev_hash || canonical_json(payload)). Any retro-edit of a past
-- decision breaks the chain, which is what makes an RTS-defensible export
-- possible without a database everyone has to trust.
CREATE TABLE IF NOT EXISTS audit_log (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    id           TEXT NOT NULL UNIQUE,
    ts           TEXT NOT NULL,
    actor        TEXT,
    actor_role   TEXT,
    action       TEXT NOT NULL,
    entity_type  TEXT,
    entity_id    TEXT,
    payload      TEXT NOT NULL,
    prev_hash    TEXT NOT NULL,
    entry_hash   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_audit_action ON audit_log(action, ts);

CREATE TABLE IF NOT EXISTS ticket_events (
    id         TEXT PRIMARY KEY,
    ticket_id  TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    event      TEXT NOT NULL,
    from_value TEXT,
    to_value   TEXT,
    actor      TEXT,
    note       TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_ticket ON ticket_events(ticket_id, created_at);

-- Daily capacity is operator-entered by design. The capability datasets are
-- explicit that a tender proves a resource *type* exists, never how many are
-- available today, so quantities start NULL and carry who verified them.
CREATE TABLE IF NOT EXISTS daily_capacity (
    id                  TEXT PRIMARY KEY,
    capacity_date       TEXT NOT NULL,
    ward_id             TEXT REFERENCES wards(id),
    budget_inr          REAL,
    workforce_hours     REAL,
    verified_by         TEXT,
    verified_at         TEXT,
    source              TEXT NOT NULL DEFAULT 'operator_entered',
    note                TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_capacity_day
    ON daily_capacity(capacity_date, IFNULL(ward_id, ''));

CREATE TABLE IF NOT EXISTS capacity_resources (
    id             TEXT PRIMARY KEY,
    capacity_id    TEXT NOT NULL REFERENCES daily_capacity(id) ON DELETE CASCADE,
    resource_type  TEXT NOT NULL,
    display_name   TEXT,
    available_now  INTEGER,
    quantity_known INTEGER NOT NULL DEFAULT 0,
    hourly_rate_inr REAL,
    rate_source    TEXT,
    note           TEXT,
    UNIQUE(capacity_id, resource_type)
);

CREATE TABLE IF NOT EXISTS app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def init_db(verbose: bool = False) -> None:
    """Create every table/index if missing, then run additive migrations.

    Safe to call on each startup and from tests.
    """
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        _run_migrations(conn)
        conn.execute(
            "INSERT INTO app_meta(key, value) VALUES('schema_initialised_at', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (utcnow_iso(),))
    if verbose:
        print(f"[db] schema ready at {settings.DB_PATH}")


# Additive-only migrations: (table, column, DDL type/default). Adding a column
# to an existing deployment must never require dropping data mid-hackathon.
MIGRATIONS: list[tuple[str, str, str]] = [
    ("tickets", "closure_note", "TEXT"),
    ("tickets", "duration_hours", "REAL"),
    ("tickets", "candidate_equipment", "TEXT"),
    # Added after the first schema cut: recurrence is not duplication, and the
    # escalating conditions must be stored as confirmed booleans rather than
    # inferred from free text.
    ("tickets", "recurrence_of_id", "TEXT REFERENCES tickets(id)"),
    ("tickets", "dedup_evidence", "TEXT"),
    ("tickets", "blocks_major_road", "INTEGER NOT NULL DEFAULT 0"),
    ("tickets", "access_isolated", "INTEGER NOT NULL DEFAULT 0"),
    ("tickets", "critical_facility_isolated", "INTEGER NOT NULL DEFAULT 0"),
    ("tickets", "cost_inputs", "TEXT"),
    ("tickets", "criteria_flags", "TEXT"),
    ("tickets", "overall_confidence", "REAL"),
]


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.Error:
        return set()
    return {r["name"] for r in rows}


def _run_migrations(conn: sqlite3.Connection) -> None:
    for table, column, ddl in MIGRATIONS:
        cols = _table_columns(conn, table)
        if cols and column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


# ---------------------------------------------------------------------------
# criteria definitions
# ---------------------------------------------------------------------------
# C1-C4 come verbatim from the project's criteria definition. C4 is a *cost*
# criterion: a higher resource requirement must lower the closeness coefficient.
CRITERIA: list[str] = ["C1_infra", "C2_safety", "C3_equity", "C4_cost"]

CRITERIA_TYPES: dict[str, str] = {
    "C1_infra": "benefit",
    "C2_safety": "benefit",
    "C3_equity": "benefit",
    "C4_cost": "cost",
}

CRITERIA_LABELS: dict[str, str] = {
    "C1_infra": "Infrastructural Criticality",
    "C2_safety": "Public Safety & Health Risk",
    "C3_equity": "Socio-Spatial Equity",
    "C4_cost": "Resource Requirement",
}

# Fallback weights used only when no CR-passing AHP version exists yet. They are
# labelled as unvalidated everywhere they surface, because no Kopargaon dataset
# supplies numeric AHP weights and inventing sourced-looking numbers is exactly
# what the brief warns against.
DEFAULT_CRITERIA_CONFIG: dict[str, Any] = {
    "names": list(CRITERIA),
    "types": [CRITERIA_TYPES[c] for c in CRITERIA],
    "weights": [[0.6, 0.8, 1.0], [0.8, 0.9, 1.0],
                [0.3, 0.5, 0.7], [0.4, 0.6, 0.8]],
    "provenance": "unvalidated_default_no_ahp_version_active",
}


if __name__ == "__main__":  # pragma: no cover
    init_db(verbose=True)

