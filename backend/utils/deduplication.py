"""Backwards-compatible shim over ``services.imaging``.

Kept so any code or notebook that still imports ``utils.deduplication`` keeps
working, but the implementation now comes from ``services.imaging`` -- pure
Python, no ``imagehash``/``scipy`` dependency, and bit-compatible with
``imagehash.phash(hash_size=8, highfreq_factor=4)``.

``is_duplicate`` is preserved *only* as a hash-distance helper and returns a
``(bool, match)`` tuple. Its old call site did ``if is_duplicate(...)``, which is
truthy for ``(False, None)`` too, so every photo report was flagged duplicate.
Unpack both values, or better, use ``services.dedup.find_duplicate``, which also
checks proximity, text and recurrence rather than the image alone.
"""
from __future__ import annotations

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.imaging import (ImageUnreadable, average_hash_from_grid,  # noqa: E402,F401
                              generate_phash, grid_from_bytes, hamming_hex,
                              hash_pair_from_bytes, similarity)

DEFAULT_THRESHOLD = 8


def hamming_distance(a: str, b: str) -> int | None:
    """Bit distance between two hex hashes, or None if they are incomparable."""
    return hamming_hex(a, b)


def is_duplicate(new_hash_str: str, existing_hashes: list[str],
                 threshold: int = DEFAULT_THRESHOLD) -> tuple[bool, str | None]:
    """Nearest hash within ``threshold`` bits.

    Returns ``(matched, matched_hash)``. **Unpack the tuple** -- the tuple itself
    is always truthy.
    """
    best, best_distance = None, None
    for candidate in existing_hashes or []:
        distance = hamming_hex(new_hash_str, candidate)
        if distance is None or distance > threshold:
            continue
        if best_distance is None or distance < best_distance:
            best, best_distance = candidate, distance
    return (best is not None), best


def nearest_hash(new_hash_str: str, existing_hashes: list[str]) -> dict:
    """Closest hash and its distance, with no threshold applied.

    Useful for auditing a near-miss: "8 bits apart, just outside the 8-bit
    threshold" is a defensible sentence, "not a duplicate" on its own is not.
    """
    best, best_distance = None, None
    for candidate in existing_hashes or []:
        distance = hamming_hex(new_hash_str, candidate)
        if distance is None:
            continue
        if best_distance is None or distance < best_distance:
            best, best_distance = candidate, distance
    return {"hash": best, "distance": best_distance,
            "similarity": similarity(new_hash_str, best) if best else None}
