"""Tamper-evident audit chain: every consequential decision, hash-linked.

The claim this module has to survive is narrow and specific: *the record of why
a citizen's complaint was ranked where it was has not been edited since it was
written.* A plain audit table cannot support that claim, because whoever can
write the table can rewrite it. So each row carries the hash of its predecessor,
and `verify` recomputes the whole chain and names the first row that stopped
agreeing with itself.

Three things are worth being precise about, because a chain that overstates what
it proves is worse than no chain at all:

* **What a break means.** `verify` distinguishes two failures. A *content* break
  means a row's own fields no longer hash to its stored `entry_hash` -- someone
  edited a payload in place. A *link* break means a row's `prev_hash` no longer
  matches its predecessor's `entry_hash` -- a row was inserted or removed in the
  middle. Both name the offending `seq`; they are not the same accusation.
* **What it cannot detect.** Truncation. Delete the newest rows and the surviving
  prefix is still perfectly self-consistent -- that is inherent to every hash
  chain without an external anchor. `verify` therefore always returns `tip_hash`
  and `tip_seq`, which is the value a council would publish, minute, or mail to
  itself so that truncation becomes detectable. We say this in the response
  rather than implying a guarantee we do not have.
* **What is hashed.** A canonical JSON form with sorted keys, so the digest does
  not depend on Python's dict ordering or on whitespace. `seq` is deliberately
  *not* in the digest: SQLite assigns it on insert, and hashing a value we do not
  yet hold would mean writing the row twice. Ordering integrity comes from
  `prev_hash`, which is what the links are for.

`append` must be called inside the caller's transaction. That is the whole point
of the docstring on `database.transaction`: if the triage run commits and the
audit row does not, the chain is intact and *wrong*, which is the one outcome
worse than a visible break.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from database import loads, new_id, query_all, query_one, utcnow_iso
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from database import loads, new_id, query_all, query_one, utcnow_iso

# The chain's first row points at nothing. 64 zeros is the conventional genesis
# value and is the same width as a SHA-256 digest, so the column never holds two
# shapes of thing.
GENESIS_PREV_HASH = "0" * 64

HASH_NAME = "sha256"

#: Said in every ``verify`` response. See the module docstring: a chain proves
#: no edit and no reorder, never no truncation.
TRUNCATION_CAVEAT = (
    "A hash chain proves nothing was edited or reordered; it cannot by itself "
    "prove nothing was removed from the end. Publish or minute tip_hash to make "
    "truncation detectable."
)

#: Actions the platform records. Keeping these as constants means a typo in a
#: caller is an ImportError rather than an audit row nobody will ever find again.
ACTION_TICKET_CREATED = "ticket.created"
ACTION_COST_EDITED = "ticket.cost_inputs_edited"
ACTION_TRIAGE_RUN = "triage.run"
ACTION_WEIGHTS_ACTIVATED = "weights.activated"
ACTION_EXPLANATION_STORED = "explanation.stored"

ENTITY_TICKET = "ticket"
ENTITY_MANIFEST = "manifest"
ENTITY_WEIGHTS = "criteria_weights"
ENTITY_EXPLANATION = "explanation"


def canonical_payload(payload: Any) -> str:
    """Stable JSON for hashing: sorted keys, no incidental whitespace.

    ``ensure_ascii=False`` matches ``database.dumps`` so a Marathi citizen
    message hashes the same way it is stored.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def compute_entry_hash(*, entry_id: str, ts: str, actor: Any, actor_role: Any,
                       action: str, entity_type: Any, entity_id: Any,
                       payload_json: str, prev_hash: str) -> str:
    """The digest of one row.

    Fields are joined with a NUL separator rather than concatenated, so that
    moving a character across a field boundary -- actor ``"ab"``/action ``"c"``
    versus actor ``"a"``/action ``"bc"`` -- cannot produce the same digest.
    """
    parts = [entry_id, ts, actor or "", actor_role or "", action,
             entity_type or "", entity_id or "", payload_json, prev_hash]
    joined = "\x00".join(str(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def tip(conn) -> dict | None:
    """The newest row, or None on an empty chain."""
    row = query_one(conn, "SELECT seq, id, entry_hash FROM audit_log "
                          "ORDER BY seq DESC LIMIT 1")
    return dict(row) if row else None


def append(conn, action: str, *, payload: Any = None,
           entity_type: str | None = None, entity_id: str | None = None,
           actor: str | None = None, actor_role: str | None = None) -> dict:
    """Add one row, linked to whatever is currently the tip.

    Call inside the caller's transaction. The read of the tip and the insert must
    not be separated by another writer, which ``BEGIN IMMEDIATE`` in
    ``database.transaction`` is what guarantees -- two concurrent appends would
    otherwise both claim the same predecessor and leave a fork.
    """
    previous = tip(conn)
    prev_hash = previous["entry_hash"] if previous else GENESIS_PREV_HASH
    entry_id = new_id()
    ts = utcnow_iso()
    payload_json = canonical_payload(payload if payload is not None else {})
    entry_hash = compute_entry_hash(
        entry_id=entry_id, ts=ts, actor=actor, actor_role=actor_role,
        action=action, entity_type=entity_type, entity_id=entity_id,
        payload_json=payload_json, prev_hash=prev_hash)
    conn.execute(
        "INSERT INTO audit_log(id, ts, actor, actor_role, action, entity_type, "
        "entity_id, payload, prev_hash, entry_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (entry_id, ts, actor, actor_role, action, entity_type, entity_id,
         payload_json, prev_hash, entry_hash))
    seq = conn.execute("SELECT seq FROM audit_log WHERE id = ?",
                       (entry_id,)).fetchone()["seq"]
    return {"seq": int(seq), "id": entry_id, "ts": ts, "action": action,
            "entity_type": entity_type, "entity_id": entity_id,
            "prev_hash": prev_hash, "entry_hash": entry_hash}


def try_append(conn, action: str, **kwargs) -> dict | None:
    """``append`` that swallows its own failure.

    Used from paths where an unwritable audit row must not lose a citizen's
    complaint -- ingestion, above all. The failure is reported in the return
    value so a caller that cares can surface it, and the primary write proceeds.
    Anything that is *itself* a compliance act (weight activation, a triage run)
    calls ``append`` directly and is allowed to fail loudly.
    """
    try:
        return append(conn, action, **kwargs)
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
        return {"appended": False,
                "error": f"{type(exc).__name__}: {exc}",
                "action": action}


def _recompute(row: Any) -> str:
    return compute_entry_hash(
        entry_id=row["id"], ts=row["ts"], actor=row["actor"],
        actor_role=row["actor_role"], action=row["action"],
        entity_type=row["entity_type"], entity_id=row["entity_id"],
        payload_json=row["payload"], prev_hash=row["prev_hash"])


def verify(conn) -> dict:
    """Walk the chain in ``seq`` order and report the first row that breaks it.

    Returns 200-shaped data in every case, including a broken chain: a tampered
    audit log is a finding to display, not a server error. An empty chain is
    ``ok: true`` with ``entries: 0`` -- nothing has happened yet, which is a
    truthful answer and not a failure.
    """
    rows = query_all(conn, "SELECT seq, id, ts, actor, actor_role, action, "
                           "entity_type, entity_id, payload, prev_hash, "
                           "entry_hash FROM audit_log ORDER BY seq ASC")
    if not rows:
        return {
            "ok": True, "entries": 0, "algorithm": HASH_NAME,
            "genesis_prev_hash": GENESIS_PREV_HASH,
            "first_broken_seq": None, "break_type": None, "reason": None,
            "tip_seq": None, "tip_hash": None,
            "checked_at": utcnow_iso(),
            "message": "the audit chain is empty: nothing has been recorded yet",
            "truncation_caveat": TRUNCATION_CAVEAT,
        }

    expected_prev = GENESIS_PREV_HASH
    for row in rows:
        seq = int(row["seq"])
        if row["prev_hash"] != expected_prev:
            return _broken(
                rows, seq, "link",
                f"entry {seq} records prev_hash {_short(row['prev_hash'])} but "
                f"its predecessor hashes to {_short(expected_prev)}; a row was "
                f"inserted or removed at or before this point")
        recomputed = _recompute(row)
        if recomputed != row["entry_hash"]:
            return _broken(
                rows, seq, "content",
                f"entry {seq} ({row['action']}) no longer hashes to its stored "
                f"entry_hash: recomputed {_short(recomputed)}, stored "
                f"{_short(row['entry_hash'])}; this row's contents were edited "
                f"after it was written")
        expected_prev = row["entry_hash"]

    last = rows[-1]
    return {
        "ok": True, "entries": len(rows), "algorithm": HASH_NAME,
        "genesis_prev_hash": GENESIS_PREV_HASH,
        "first_broken_seq": None, "break_type": None, "reason": None,
        "tip_seq": int(last["seq"]), "tip_hash": last["entry_hash"],
        "checked_at": utcnow_iso(),
        "message": (f"all {len(rows)} entries verify: every row hashes to its "
                    f"stored digest and every link matches its predecessor"),
        "truncation_caveat": TRUNCATION_CAVEAT,
    }


def _short(digest: Any) -> str:
    text = str(digest or "")
    return f"{text[:12]}..." if len(text) > 12 else text


def _broken(rows: list, seq: int, break_type: str, reason: str) -> dict:
    """Assemble the failure body. The verified prefix is still worth reporting:
    'the first 412 entries are intact and entry 413 is not' is far more useful to
    an officer than 'the chain is broken'."""
    last = rows[-1]
    return {
        "ok": False, "entries": len(rows), "algorithm": HASH_NAME,
        "genesis_prev_hash": GENESIS_PREV_HASH,
        "first_broken_seq": seq, "break_type": break_type, "reason": reason,
        "verified_prefix": seq - 1,
        "tip_seq": int(last["seq"]), "tip_hash": last["entry_hash"],
        "checked_at": utcnow_iso(),
        "message": (f"the audit chain breaks at entry {seq}: entries 1-{seq - 1} "
                    f"verify, entry {seq} does not"),
        "truncation_caveat": TRUNCATION_CAVEAT,
    }


def _public(row: Any) -> dict:
    """One row as the API returns it, with the payload inflated back to JSON."""
    out = dict(row)
    out["seq"] = int(out["seq"])
    out["payload"] = loads(out.get("payload"), {})
    return out


def recent(conn, limit: int = 50, *, action: str | None = None) -> list[dict]:
    """Newest entries first -- the compliance page's activity feed."""
    sql = ("SELECT seq, id, ts, actor, actor_role, action, entity_type, "
           "entity_id, payload, prev_hash, entry_hash FROM audit_log")
    params: list[Any] = []
    if action:
        sql += " WHERE action = ?"
        params.append(action)
    sql += " ORDER BY seq DESC LIMIT ?"
    params.append(int(limit))
    return [_public(r) for r in query_all(conn, sql, params)]


def for_entity(conn, entity_type: str, entity_id: str,
               limit: int = 200) -> list[dict]:
    """Everything recorded against one thing, oldest first.

    Oldest first on purpose: this is read as a narrative of what happened to a
    ticket, not as a feed.
    """
    rows = query_all(conn, "SELECT seq, id, ts, actor, actor_role, action, "
                           "entity_type, entity_id, payload, prev_hash, "
                           "entry_hash FROM audit_log WHERE entity_type = ? "
                           "AND entity_id = ? ORDER BY seq ASC LIMIT ?",
                     (entity_type, entity_id, int(limit)))
    return [_public(r) for r in rows]


def export_for_ticket(conn, ticket_id: str, limit: int = 500) -> dict:
    """Every entry that mentions one ticket, for an RTS reply or an appeal.

    Rows filed *against* the ticket are the obvious half. The other half matters
    more: the triage run that deferred it names it only inside its payload, and
    that run is usually the entry the citizen is actually asking about. So the
    payload is searched too, and each row is labelled with how it was matched --
    an officer attaching this to a reply should not have to guess why a
    manifest-level entry is in a single citizen's file.
    """
    row = query_one(conn, "SELECT id, ref_no FROM tickets WHERE id = ? OR "
                          "ref_no = ?", (ticket_id, ticket_id))
    resolved_id = row["id"] if row else ticket_id
    ref_no = row["ref_no"] if row else None

    direct = query_all(conn, "SELECT seq, id, ts, actor, actor_role, action, "
                             "entity_type, entity_id, payload, prev_hash, "
                             "entry_hash FROM audit_log WHERE entity_id = ? "
                             "ORDER BY seq ASC LIMIT ?", (resolved_id, limit))
    seen = {int(r["seq"]) for r in direct}
    entries = [{**_public(r), "matched_on": "entity_id"} for r in direct]

    # LIKE on the canonical payload. The id is a uuid4, so a substring hit is not
    # a coincidence; the ref_no is checked too because citizen-facing payloads
    # carry that rather than the internal id.
    for needle in filter(None, (resolved_id, ref_no)):
        for r in query_all(conn, "SELECT seq, id, ts, actor, actor_role, action, "
                                 "entity_type, entity_id, payload, prev_hash, "
                                 "entry_hash FROM audit_log WHERE payload LIKE ? "
                                 "ORDER BY seq ASC LIMIT ?",
                           (f"%{needle}%", limit)):
            if int(r["seq"]) not in seen:
                seen.add(int(r["seq"]))
                entries.append({**_public(r), "matched_on": "payload_reference"})

    entries.sort(key=lambda e: e["seq"])
    chain = verify(conn)
    return {
        "ticket_id": resolved_id,
        "ref_no": ref_no,
        "ticket_found": row is not None,
        "count": len(entries),
        "entries": entries,
        "chain": {k: chain[k] for k in
                  ("ok", "entries", "first_broken_seq", "break_type",
                   "tip_seq", "tip_hash", "algorithm")},
        "exported_at": utcnow_iso(),
        "note": ("Verify the chain before relying on this export. An export from "
                 "a chain that does not verify is evidence of what the table "
                 "currently says, not of what was originally recorded."),
    }


def stats(conn) -> dict:
    """Counts per action plus the chain's extent -- the compliance header."""
    rows = query_all(conn, "SELECT action, COUNT(*) AS n FROM audit_log "
                           "GROUP BY action ORDER BY n DESC")
    span = query_one(conn, "SELECT MIN(ts) AS first_ts, MAX(ts) AS last_ts, "
                           "COUNT(*) AS n FROM audit_log")
    return {
        "entries": int(span["n"]) if span else 0,
        "first_ts": span["first_ts"] if span else None,
        "last_ts": span["last_ts"] if span else None,
        "by_action": [{"action": r["action"], "count": int(r["n"])}
                      for r in rows],
        "actions_recorded": [ACTION_TICKET_CREATED, ACTION_COST_EDITED,
                             ACTION_TRIAGE_RUN, ACTION_WEIGHTS_ACTIVATED,
                             ACTION_EXPLANATION_STORED],
    }
