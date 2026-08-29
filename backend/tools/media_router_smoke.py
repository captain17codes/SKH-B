"""Exercise routers/media.py without FastAPI installed.

The triage harness's fixture has no photographs, and photographs are the entire
point of this router, so this one seeds its own: two near-identical images taken
metres apart (which must merge) and the same image four kilometres away (which
must not). What is being tested is that the merge the dedup service performed is
*retrievable as evidence* -- parent, children, hash distance, metres apart, and a
readable file for each -- because an unviewable merge is an unaccountable one.

Also asserted: the traversal guard. A media row whose ``file_path`` points
outside ``UPLOAD_DIR`` must 404 rather than serve the file, since a restored or
hand-edited database is untrusted input.

Run:  python3 tools/media_router_smoke.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tools"))

# Installs the fastapi/pydantic stand-ins and redirects CRPP_DB_PATH/UPLOAD_DIR
# to a wiped scratch directory. Must precede every first-party import.
import triage_router_smoke as harness  # noqa: E402

# routers/media.py imports FileResponse, which the triage harness does not stub.
import types  # noqa: E402


class _FileResponse:
    """Records what would have been sent instead of building an HTTP response."""

    def __init__(self, path, media_type=None, filename=None):
        self.path = Path(path)
        self.media_type = media_type
        self.filename = filename
        self.size = self.path.stat().st_size if self.path.is_file() else None


responses = types.ModuleType("fastapi.responses")
responses.FileResponse = _FileResponse
sys.modules["fastapi.responses"] = responses
sys.modules["fastapi"].responses = responses

HTTPException = harness.HTTPException

from config import settings  # noqa: E402
from database import execute, get_conn, init_db, query_one  # noqa: E402
from routers import media as api  # noqa: E402
from services import tickets as ticket_service  # noqa: E402

KOP_LAT, KOP_LON = 19.8872, 74.4772


def photo(seed: int, jitter: int = 0, quality: int = 92) -> bytes:
    """A deterministic 8x8 block pattern, JPEG-re-encoded.

    Same generator as the demo seed. ``jitter`` nudges a few blocks so the two
    "same drain" photographs are not byte-identical -- a merge that only works on
    identical files would prove nothing about perceptual hashing.
    """
    from PIL import Image

    img = Image.new("RGB", (8, 8))
    px = img.load()
    for y in range(8):
        for x in range(8):
            v = (seed * 37 + x * 29 + y * 17) % 256
            if jitter and (x + y) % 5 == 0:
                v = (v + jitter) % 256
            px[x, y] = (v, (v * 3) % 256, (v * 7) % 256)
    img = img.resize((220, 220), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _expect_404(fn, *args, **kwargs) -> str:
    try:
        fn(*args, **kwargs)
    except HTTPException as exc:
        assert exc.status_code == 404, exc
        return exc.detail
    raise AssertionError(f"{getattr(fn, '__name__', fn)} should have raised 404")


def _make(conn, key, desc, lat, lon, image, phone="9000000001"):
    uploads = [{"filename": f"{key}.jpg", "content": image}] if image else []
    return ticket_service.create_ticket(
        conn, {"citizen_phone": phone, "category": "drain_blockage",
               "description": desc, "ward_id": "W3", "lat": lat, "lon": lon},
        uploads, actor="media_smoke")


def _decision(created: dict) -> str:
    """``create_ticket`` nests the dedup verdict; the smoke test only wants it."""
    return created["dedup"]["decision"]


def main() -> None:
    init_db()
    same = photo(11)
    nudged = photo(11, jitter=4, quality=60)
    with get_conn() as conn:
        routes = sorted(api.router.routes)
        print("registered routes:")
        for method, path, name in routes:
            print(f"   {method:<4} {path:<34} {name}")
        for expected in (("GET", "/api/media/ticket/{ticket_id}",
                          "media_for_ticket"),
                         ("GET", "/api/media/index", "media_index"),
                         ("GET", "/api/media/{media_id}/file", "media_file"),
                         ("GET", "/api/media/clusters", "clusters"),
                         ("GET", "/api/media/cluster/{ticket_id}", "cluster")):
            assert expected in routes, f"missing route {expected}"

        parent = _make(conn, "drain_a", "storm drain overflowing at the corner",
                       KOP_LAT, KOP_LON, same)
        pid = parent["ticket_id"]
        assert _decision(parent) == "unique", parent["dedup"]

        # ~12 m north, same scene, re-encoded harder: must merge on the image.
        near = _make(conn, "drain_b", "same drain still overflowing here",
                     KOP_LAT + 0.00011, KOP_LON, nudged, phone="9000000002")
        assert _decision(near) == "duplicate", near["dedup"]
        # ~4 km away, identical image: must NOT merge.
        far = _make(conn, "drain_c", "drain overflowing on the far side of town",
                    19.9200, 74.5100, same, phone="9000000003")
        assert _decision(far) == "unique", far["dedup"]
        print(f"\nseeded: parent {parent['ref_no']}, near-duplicate merged, "
              f"far look-alike kept separate  OK")

        # ---- GET /api/media/ticket/{ticket_id} ------------------------------
        listing = api.media_for_ticket(pid, conn=conn)
        assert listing["ticket_id"] == pid
        assert listing["ref_no"] == parent["ref_no"]
        assert listing["count"] == 1, listing
        img = listing["media"][0]
        assert img["available"] is True, img
        assert img["unavailable_reason"] is None, img
        assert img["phash"], "the seeded photograph produced no perceptual hash"
        assert img["url"] == f"/api/media/{img['id']}/file", img["url"]
        assert img["size_bytes"] and img["size_bytes"] > 0, img
        print(f"\n/ticket/{{id}}  count={listing['count']} "
              f"phash={img['phash']} bits={img['phash_bits']} "
              f"size={img['size_bytes']}B available={img['available']}")

        # A ticket that exists but has no photograph is a valid empty answer,
        # not a 404: a report from somebody without a camera is still a report.
        textonly = _make(conn, "no_photo", "no camera, reporting by phone call",
                         19.9500, 74.5500, None, phone="9000000004")
        empty = api.media_for_ticket(textonly["ticket_id"], conn=conn)
        assert empty["count"] == 0 and empty["media"] == [], empty
        print(f"/ticket/{{id}}  photo-less ticket -> count=0, not 404  OK")
        detail = _expect_404(api.media_for_ticket, "no-such-ticket", conn=conn)
        print(f"/ticket/{{id}}  unknown ticket -> 404 {detail!r}")

        # ---- GET /api/media/index -------------------------------------------
        # One request for a whole table. Tickets without a photograph are absent
        # from the map rather than present-and-empty, so the caller can test with
        # a plain lookup.
        wanted = [pid, near["ticket_id"], far["ticket_id"],
                  textonly["ticket_id"], "no-such-ticket"]
        idx = api.media_index(ticket_ids=",".join(wanted), conn=conn)
        assert idx["requested"] == 5, idx["requested"]
        assert idx["count"] == 3, idx["count"]
        assert set(idx["tickets"]) == {pid, near["ticket_id"], far["ticket_id"]}
        assert textonly["ticket_id"] not in idx["tickets"]
        assert idx["tickets"][pid][0]["id"] == img["id"]
        blank = api.media_index(ticket_ids="  ,  ", conn=conn)
        assert blank == {"tickets": {}, "count": 0, "requested": 0}, blank
        every = api.media_index(conn=conn)
        assert every["count"] == 3 and every["requested"] == 0, every
        print(f"\n/index  asked about {idx['requested']} tickets in ONE request; "
              f"{len(idx['tickets'])} have images ({idx['count']} total), "
              f"photo-less ticket correctly absent")

        # ---- GET /api/media/{media_id}/file --------------------------------
        # The stored path must be *relative* to UPLOAD_DIR. An absolute path
        # bakes this machine's directory layout into the data, so a database
        # carried to the demo laptop would report every photograph as lying
        # outside the upload directory.
        stored_path = query_one(
            conn, "SELECT file_path FROM ticket_media WHERE id = ?",
            (img["id"],))["file_path"]
        assert not Path(stored_path).is_absolute(), stored_path
        assert stored_path.startswith(f"{pid}/"), stored_path
        print(f"\nstored file_path is relative to UPLOAD_DIR: {stored_path!r}  OK")

        served = api.media_file(img["id"], conn=conn)
        assert served.size == img["size_bytes"], (served.size, img)
        assert served.media_type == "image/jpeg", served.media_type
        assert served.path.is_file()
        head = served.path.read_bytes()[:3]
        assert head == b"\xff\xd8\xff", head  # a real JPEG, not a stub
        print(f"\n/{{media_id}}/file  {served.filename} {served.media_type} "
              f"{served.size}B  JPEG magic OK")
        detail = _expect_404(api.media_file, "no-such-media", conn=conn)
        print(f"/{{media_id}}/file  unknown id -> 404 {detail!r}")

        # ---- GET /api/media/clusters ---------------------------------------
        bundle = api.clusters(limit=20, conn=conn)
        assert bundle["count"] >= 1, bundle
        cl = next(c for c in bundle["clusters"] if c["ticket_id"] == pid)
        assert cl["report_count"] == 2, cl["report_count"]
        assert cl["duplicate_count"] == 1, cl["duplicate_count"]
        assert cl["merge_bases"] == ["perceptual_image_match"], cl["merge_bases"]
        assert cl["primary_media"] and cl["primary_media"]["available"]
        assert len(cl["duplicate_media"]) == 1, cl["duplicate_media"]
        # The far look-alike was never merged, so it must not appear here.
        assert far["ticket_id"] not in {c["ticket_id"] for c in bundle["clusters"]}
        print(f"\n/clusters  {bundle['count']} cluster(s); {cl['ref_no']} "
              f"report_count={cl['report_count']} "
              f"multiplier={cl['community_multiplier']} "
              f"bases={cl['merge_bases']} "
              f"parent_image+{len(cl['duplicate_media'])} duplicate image(s)")

        # ---- GET /api/media/cluster/{ticket_id} ----------------------------
        for queried, label in ((pid, "parent"), (near["ticket_id"], "child")):
            view = api.cluster(queried, conn=conn)
            assert view["queried_ticket_id"] == queried
            assert view["parent_ticket_id"] == pid, view["parent_ticket_id"]
            assert view["is_cluster"] is True
            assert view["duplicate_count"] == 1, view
            roles = [m["role"] for m in view["members"]]
            assert roles == ["parent", "duplicate"], roles
            child = view["members"][1]
            m = child["match"]
            assert m["basis"] == "perceptual_image_match", m
            assert m["hash_distance"] is not None and m["hash_distance"] <= 4, m
            assert 0 < m["distance_meters"] <= 150, m
            assert m["reason"], m
            assert child["media"] and child["media"][0]["available"]
            print(f"\n/cluster/{{id}} via {label}: parent {view['parent_ref_no']} "
                  f"report_count={view['report_count']} "
                  f"members={roles}")
            print(f"   verdict: {m['basis']} conf={m['confidence']} "
                  f"hamming={m['hash_distance']} "
                  f"({m['hash_similarity']}) "
                  f"{m['distance_meters']} m apart, "
                  f"text_sim={m['text_similarity']}")
            print(f"   reason : {m['reason']}")
        assert view["policy"]["hamming_threshold"] == int(
            settings.DEDUPE_HAMMING_THRESHOLD)
        assert view["policy"]["radius_meters"] == float(
            settings.DEDUPE_RADIUS_METERS)

        # A ticket with no cluster still answers, honestly.
        lone = api.cluster(far["ticket_id"], conn=conn)
        assert lone["is_cluster"] is False and lone["duplicate_count"] == 0, lone
        assert [m["role"] for m in lone["members"]] == ["parent"], lone
        print(f"\n/cluster/{{id}}  un-merged ticket {lone['parent_ref_no']} -> "
              f"is_cluster=False, members=['parent']  OK")
        detail = _expect_404(api.cluster, "no-such-ticket", conn=conn)
        print(f"/cluster/{{id}}  unknown ticket -> 404 {detail!r}")

        # ---- the untrusted-row guards --------------------------------------
        # Everything below rewrites a stored file_path directly, which is the
        # one way a bad path can reach this router: the URL only ever carries a
        # media_id. A database restored from another machine, or hand-edited,
        # is untrusted input and must not be able to make the service read an
        # arbitrary file off disk.
        mid, real_path = img["id"], served.path
        outside = Path(settings.UPLOAD_DIR).resolve().parent / "escaped.jpg"
        outside.write_bytes(real_path.read_bytes())
        traversal = str(Path(settings.UPLOAD_DIR) / ".." / outside.name)
        for label, stored in (("absolute path outside UPLOAD_DIR", str(outside)),
                              ("relative ../ traversal", traversal),
                              ("absolute path to a system file", "/etc/hostname")):
            execute(conn, "UPDATE ticket_media SET file_path = ? WHERE id = ?",
                    (stored, mid))
            detail = _expect_404(api.media_file, mid, conn=conn)
            assert "upload directory" in detail, detail
            row = dict(query_one(conn,
                                 "SELECT * FROM ticket_media WHERE id = ?", (mid,)))
            view = api._media_view(row)
            assert view["available"] is False, view
            assert "outside the configured upload" in view["unavailable_reason"]
            print(f"\nguard: {label}\n   -> 404 {detail!r}\n"
                  f"   -> listing says available=False, "
                  f"reason={view['unavailable_reason']!r}")
        outside.unlink()

        # Inside UPLOAD_DIR but the pixels are gone: a different 404, because
        # "someone tried to escape the directory" and "the file was deleted"
        # are different problems for whoever reads the log.
        ghost = str(Path(settings.UPLOAD_DIR) / "deleted" / "gone.jpg")
        execute(conn, "UPDATE ticket_media SET file_path = ? WHERE id = ?",
                (ghost, mid))
        detail = _expect_404(api.media_file, mid, conn=conn)
        assert "not present on this host" in detail, detail
        view = api._media_view(dict(query_one(
            conn, "SELECT * FROM ticket_media WHERE id = ?", (mid,))))
        assert view["unavailable_reason"] == (
            "the image file is not present on this host"), view
        print(f"\nguard: path inside UPLOAD_DIR but file deleted\n"
              f"   -> 404 {detail!r}\n"
              f"   -> reason={view['unavailable_reason']!r}")

        execute(conn, "UPDATE ticket_media SET file_path = NULL WHERE id = ?",
                (mid,))
        detail = _expect_404(api.media_file, mid, conn=conn)
        view = api._media_view(dict(query_one(
            conn, "SELECT * FROM ticket_media WHERE id = ?", (mid,))))
        assert view["unavailable_reason"] == "no file path recorded for this image"
        print(f"\nguard: file_path IS NULL\n   -> 404 {detail!r}\n"
              f"   -> reason={view['unavailable_reason']!r}")

        # Put the row back so the database is left consistent for inspection.
        execute(conn, "UPDATE ticket_media SET file_path = ? WHERE id = ?",
                (str(real_path), mid))
        assert api.media_file(mid, conn=conn).size == img["size_bytes"]

    print("\nall media router checks passed")


if __name__ == "__main__":
    main()
