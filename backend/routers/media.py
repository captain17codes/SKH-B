"""Citizen photographs, and the visual evidence behind a duplicate merge.

The deduplication story is the one part of this system that cannot be argued in
numbers alone. "pHash distance 0 at 12 m, therefore one ticket instead of three"
is a claim; two photographs side by side is the proof. Until now the images were
written to disk and hashed and then never served, so the most persuasive evidence
in the database was invisible to the officer who has to defend the merge -- and
to the citizen who wants to know why their report shows as a duplicate of
somebody else's.

Three endpoints, deliberately narrow:

* ``GET /api/media/ticket/{ticket_id}``  what images a ticket has, with the hash
  that was computed from each one.
* ``GET /api/media/index?ticket_ids=``   the same thing for a whole table at
  once, so a queue screen costs one request rather than one per row.
* ``GET /api/media/{media_id}/file``     the bytes.
* ``GET /api/media/cluster/{ticket_id}`` the merge itself: the surviving parent,
  every report folded into it, and for each the stored verdict -- hash distance,
  metres apart, text overlap, and the sentence the matcher wrote at the time.

Two safety notes, since this is the only route in the service that reads from the
filesystem. Files are addressed by ``media_id`` and the path comes from the
database row, never from the URL, so there is no traversal surface; and the
resolved path is still checked to be inside ``UPLOAD_DIR`` before a single byte
is read, because a bad row is as dangerous as a bad request. Like every other
endpoint here this one is unauthenticated while ``ENFORCE_AUTH`` is false, which
means anyone who can reach the port can read citizen photographs -- acceptable on
localhost for the build, and the reason ``ENFORCE_AUTH`` exists.
"""
from __future__ import annotations

import mimetypes
import os
import sqlite3
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # noqa: E402
from database import get_db, loads, query_all, query_one  # noqa: E402

router = APIRouter(prefix="/api/media", tags=["media"])


def _upload_root() -> Path:
    return Path(settings.UPLOAD_DIR).resolve()


def _safe_path(file_path: str | None) -> Path | None:
    """Resolve a stored path, refusing anything that escapes ``UPLOAD_DIR``.

    A stored row is trusted input right up until it isn't: a path assembled from
    a filename a citizen chose, or a database restored from elsewhere, can point
    anywhere. Checking containment here means the read is safe no matter how the
    row got written.
    """
    if not file_path:
        return None
    root = _upload_root()
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if resolved != root and root not in resolved.parents:
        return None
    return resolved


def _media_view(row: dict) -> dict:
    """One image as the UI needs it, honest about whether the file is still there.

    ``available`` is computed from the filesystem rather than assumed from the
    row, because a database copied between machines keeps its media rows while
    leaving the pixels behind. An <img> pointed at a missing file shows a broken
    icon and no explanation; this lets the page say "file not on this host".

    The three ways an image can be unavailable are reported separately on
    purpose. "Not on this host" sends somebody looking for a lost file;
    "outside the upload directory" means the *row* is wrong and no amount of
    looking will help. Collapsing them would waste the reader's time.
    """
    stored = row.get("file_path")
    path = _safe_path(stored)
    exists = bool(path and path.is_file())
    if exists:
        reason = None
    elif not stored:
        reason = "no file path recorded for this image"
    elif path is None:
        reason = ("the recorded path lies outside the configured upload "
                  "directory and will not be served")
    else:
        reason = "the image file is not present on this host"
    return {
        "id": row.get("id"),
        "ticket_id": row.get("ticket_id"),
        "media_type": row.get("media_type") or "image",
        "phash": row.get("phash"),
        "phash_bits": row.get("phash_bits"),
        "width": row.get("width"),
        "height": row.get("height"),
        "size_bytes": row.get("size_bytes"),
        "captured_at": row.get("captured_at"),
        "created_at": row.get("created_at"),
        # relative on purpose: the caller already knows the API base URL, and
        # hard-coding a host here breaks the moment this runs anywhere else.
        "url": f"/api/media/{row.get('id')}/file",
        "available": exists,
        "unavailable_reason": reason,
    }


def _media_for(conn, ticket_id: str) -> list[dict]:
    rows = query_all(conn, "SELECT * FROM ticket_media WHERE ticket_id = ? "
                           "ORDER BY created_at", (ticket_id,))
    return [_media_view(dict(r)) for r in rows]


@router.get("/ticket/{ticket_id}")
def media_for_ticket(ticket_id: str,
                     conn: sqlite3.Connection = Depends(get_db)):
    """Every image on one ticket, with the hash each one produced.

    Returning an empty list is a valid answer, not an error: a report made by
    somebody without a smartphone camera is still a report, and the queue must
    never treat "no photo" as "no complaint".
    """
    ticket = query_one(conn, "SELECT id, ref_no FROM tickets WHERE id = ?",
                       (ticket_id,))
    if ticket is None:
        raise HTTPException(status_code=404,
                            detail=f"ticket {ticket_id} not found")
    media = _media_for(conn, ticket_id)
    return {
        "ticket_id": ticket_id,
        "ref_no": ticket["ref_no"],
        "count": len(media),
        "media": media,
    }


@router.get("/index")
def media_index(ticket_ids: str | None = Query(
                    None, description="comma-separated ticket ids; omit for the "
                                      "most recent images across all tickets"),
                limit: int = Query(400, ge=1, le=2000),
                conn: sqlite3.Connection = Depends(get_db)):
    """Thumbnails for a whole table in one request.

    The queue screen shows one row per complaint and wants a photograph in each.
    Asking per row is N requests for one screen, so this answers the question the
    table actually has: "of these ids, which have images?" Tickets with no
    photograph are simply absent from the map, which the caller should read as
    "show the category icon", not as an error.

    Declared before ``/{media_id}/file`` in the source but registered on a fixed
    path, so ``/index`` can never be mistaken for a media id.
    """
    if ticket_ids:
        ids = [t.strip() for t in ticket_ids.split(",") if t.strip()]
        if not ids:
            return {"tickets": {}, "count": 0, "requested": 0}
        # Chunked because sqlite caps the number of bound parameters, and a
        # busy queue screen can legitimately ask about several hundred tickets.
        rows: list[dict] = []
        for start in range(0, len(ids), 400):
            chunk = ids[start:start + 400]
            marks = ",".join("?" * len(chunk))
            rows.extend(dict(r) for r in query_all(
                conn, f"SELECT * FROM ticket_media WHERE ticket_id IN ({marks}) "
                      f"ORDER BY created_at", tuple(chunk)))
        requested = len(ids)
    else:
        rows = [dict(r) for r in query_all(
            conn, "SELECT * FROM ticket_media ORDER BY created_at DESC LIMIT ?",
            (limit,))]
        requested = 0

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["ticket_id"], []).append(_media_view(row))
    return {"tickets": grouped, "count": len(rows), "requested": requested}


@router.get("/{media_id}/file")
def media_file(media_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """The image bytes. 404 with a reason, never a silent empty response."""
    row = query_one(conn, "SELECT * FROM ticket_media WHERE id = ?", (media_id,))
    if row is None:
        raise HTTPException(status_code=404, detail=f"media {media_id} not found")
    path = _safe_path(row["file_path"])
    if path is None:
        raise HTTPException(
            status_code=404,
            detail=(f"media {media_id} has no readable file path inside the "
                    f"configured upload directory"))
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(f"media {media_id} is recorded in the database but the file "
                    f"is not present on this host"))
    guessed = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=guessed, filename=path.name)


@router.get("/clusters")
def clusters(limit: int = Query(20, ge=1, le=200),
             conn: sqlite3.Connection = Depends(get_db)):
    """Every surviving ticket that absorbed at least one other report.

    Ordered by how many reports were folded in, because that is the ordering the
    triage screen wants: the complaint fifteen people reported is a different
    civic fact from the one person reported, and the community multiplier that
    follows from it is the part of the score most likely to be challenged.

    Declared before ``/cluster/{ticket_id}`` would be ambiguous, so note the
    paths differ (``clusters`` vs ``cluster``) and cannot collide.
    """
    rows = query_all(
        conn,
        "SELECT * FROM tickets WHERE is_duplicate = 0 AND report_count > 1 "
        "ORDER BY report_count DESC, reported_at DESC LIMIT ?", (limit,))
    out = []
    for row in rows:
        row = dict(row)
        children = [dict(r) for r in query_all(
            conn, "SELECT * FROM tickets WHERE duplicate_of_id = ? "
                  "ORDER BY reported_at", (row["id"],))]
        media = _media_for(conn, row["id"])
        bases = [(loads(c.get("dedup_evidence"), {}) or {}).get("basis")
                 for c in children]
        out.append({
            "ticket_id": row["id"],
            "ref_no": row["ref_no"],
            "category": row["category"],
            "description": row["description"],
            "ward_id": row["ward_id"],
            "lat": row["lat"],
            "lon": row["lon"],
            "status": row["status"],
            "reported_at": row["reported_at"],
            "report_count": row["report_count"],
            "community_multiplier": row["community_multiplier"],
            "duplicate_count": len(children),
            "merge_bases": sorted({b for b in bases if b}),
            "primary_media": media[0] if media else None,
            "duplicate_media": [m for c in children
                                for m in _media_for(conn, c["id"])],
        })
    return {"clusters": out, "count": len(out)}


def _cluster_member(conn, row: dict, role: str) -> dict:
    """One report in a cluster, carrying the verdict recorded when it was merged.

    The verdict is read from the child's stored ``dedup_evidence`` rather than
    recomputed. Recomputing would quietly answer a different question -- "would
    we merge these today?" -- and the officer defending last week's merge needs
    the numbers that were actually used at the time.
    """
    evidence = loads(row.get("dedup_evidence"), {}) or {}
    return {
        "role": role,
        "ticket_id": row.get("id"),
        "ref_no": row.get("ref_no"),
        "category": row.get("category"),
        "description": row.get("description"),
        "status": row.get("status"),
        "reported_at": row.get("reported_at"),
        "citizen_phone": row.get("citizen_phone"),
        "lat": row.get("lat"),
        "lon": row.get("lon"),
        "ward_id": row.get("ward_id"),
        "media": _media_for(conn, row.get("id")),
        "match": {
            "basis": evidence.get("basis"),
            "confidence": evidence.get("confidence"),
            "reason": evidence.get("reason"),
            "hash_distance": evidence.get("hash_distance"),
            "hash_similarity": evidence.get("hash_similarity"),
            "distance_meters": evidence.get("distance_meters"),
            "text_similarity": evidence.get("text_similarity"),
            "hours_apart": evidence.get("hours_apart"),
        } if evidence else None,
    }


@router.get("/cluster/{ticket_id}")
def cluster(ticket_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """A merge, with its evidence: the surviving ticket and every report folded in.

    Accepts either end of the link. Hand it a duplicate and it resolves to the
    surviving parent and describes the whole cluster from there, because a citizen
    following up on their own reference number should see the same cluster an
    officer sees, not a dead end.
    """
    row = query_one(conn, "SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if row is None:
        raise HTTPException(status_code=404,
                            detail=f"ticket {ticket_id} not found")
    row = dict(row)
    parent_id = row["duplicate_of_id"] or row["id"]
    if parent_id != row["id"]:
        parent_row = query_one(conn, "SELECT * FROM tickets WHERE id = ?",
                               (parent_id,))
        parent = dict(parent_row) if parent_row else row
    else:
        parent = row
    children = [dict(r) for r in query_all(
        conn, "SELECT * FROM tickets WHERE duplicate_of_id = ? "
              "ORDER BY reported_at", (parent["id"],))]
    recurrences = [dict(r) for r in query_all(
        conn, "SELECT * FROM tickets WHERE recurrence_of_id = ? "
              "ORDER BY reported_at", (parent["id"],))]
    members = ([_cluster_member(conn, parent, "parent")]
               + [_cluster_member(conn, c, "duplicate") for c in children]
               + [_cluster_member(conn, r, "recurrence") for r in recurrences])
    return {
        "queried_ticket_id": ticket_id,
        "parent_ticket_id": parent["id"],
        "parent_ref_no": parent["ref_no"],
        "report_count": parent.get("report_count") or 1,
        "community_multiplier": parent.get("community_multiplier"),
        "duplicate_count": len(children),
        "recurrence_count": len(recurrences),
        "is_cluster": bool(children or recurrences),
        "members": members,
        "policy": {
            "hamming_threshold": int(settings.DEDUPE_HAMMING_THRESHOLD),
            "radius_meters": float(settings.DEDUPE_RADIUS_METERS),
            "text_radius_meters": float(settings.DEDUPE_TEXT_RADIUS_METERS),
            "note": ("a merge needs an identity signal and a location signal; "
                     "an image match alone is never enough"),
        },
    }
