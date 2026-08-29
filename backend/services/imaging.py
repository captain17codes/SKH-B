"""Perceptual hashing for citizen photos.

Two reasons this is hand-written instead of a one-line ``imagehash.phash`` call:

* ``imagehash`` pulls in ``scipy`` for its DCT, and a municipal deployment that
  fails to install a Fortran-linked wheel should not lose duplicate detection;
* the platform has to *explain* its dedup decision, so the hash has to be a
  documented, reproducible 64-bit value rather than an opaque library artefact.

The algorithm is the standard pHash and is bit-compatible with
``imagehash.phash(img, hash_size=8, highfreq_factor=4)``: greyscale, resize to
32x32, 2-D DCT-II, keep the top-left 8x8 low-frequency block, threshold at the
median of that block, read row-major, MSB first. So a hash produced here can be
compared against one produced by ``imagehash`` on another machine.
"""
from __future__ import annotations

import io
import math
from functools import lru_cache

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except Exception:  # pragma: no cover - deployment without Pillow
    Image = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    PIL_AVAILABLE = False

HASH_SIZE = 8
HIGHFREQ_FACTOR = 4
IMG_SIZE = HASH_SIZE * HIGHFREQ_FACTOR  # 32
HASH_BITS = HASH_SIZE * HASH_SIZE       # 64


class ImageUnreadable(ValueError):
    """Raised when the uploaded bytes are not a decodable image."""


@lru_cache(maxsize=8)
def _dct_basis(n: int, keep: int) -> tuple[tuple[float, ...], ...]:
    """DCT-II basis rows for the first ``keep`` coefficients of an n-point signal.

    Only ``keep`` rows are built because pHash discards every high-frequency
    coefficient anyway -- computing the full 32-point transform would be four
    times the work for numbers we immediately throw away.
    """
    basis = []
    for k in range(keep):
        row = tuple(math.cos(math.pi * (2 * i + 1) * k / (2 * n))
                    for i in range(n))
        basis.append(row)
    return tuple(basis)


def _dct_2d_lowfreq(pixels: list[list[float]], n: int,
                    keep: int) -> list[list[float]]:
    """Top-left ``keep`` x ``keep`` block of the 2-D DCT-II of an n x n matrix.

    Separable: DCT along rows first (keeping ``keep`` columns), then down those
    columns. Orthonormal scaling is deliberately omitted -- pHash thresholds at
    the median of the block, and a positive constant scale cannot change which
    coefficients sit above the median.
    """
    basis = _dct_basis(n, keep)
    # Rows -> partial coefficients.
    stage = []
    for row in pixels:
        stage.append([sum(row[i] * b[i] for i in range(n)) for b in basis])
    # Columns of the partial result -> final low-frequency block.
    block = []
    for b in basis:
        block.append([sum(stage[i][j] * b[i] for i in range(n))
                      for j in range(keep)])
    return block


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def bits_to_hex(bits: list[bool]) -> str:
    """Pack bits MSB-first into a hex string (``imagehash`` wire format)."""
    out = []
    for start in range(0, len(bits), 4):
        nibble = 0
        for offset in range(4):
            nibble = (nibble << 1) | (1 if bits[start + offset] else 0)
        out.append(format(nibble, "x"))
    return "".join(out)


def grid_from_bytes(image_bytes: bytes) -> list[list[float]]:
    """Decode to a 32x32 greyscale matrix, EXIF rotation applied."""
    if not PIL_AVAILABLE:  # pragma: no cover
        raise ImageUnreadable("Pillow is not installed; cannot decode images")
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        img = img.convert("L").resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
    except Exception as exc:  # noqa: BLE001 - any decode failure is the same
        raise ImageUnreadable(f"unreadable image: {exc}") from exc
    flat = img.tobytes()  # mode "L" -> one byte per pixel, row-major
    return [[float(v) for v in flat[r * IMG_SIZE:(r + 1) * IMG_SIZE]]
            for r in range(IMG_SIZE)]


def phash_from_grid(grid: list[list[float]]) -> str:
    block = _dct_2d_lowfreq(grid, IMG_SIZE, HASH_SIZE)
    flat = [v for row in block for v in row]
    med = _median(flat)
    return bits_to_hex([v > med for v in flat])


def generate_phash(image_bytes: bytes) -> str:
    """64-bit perceptual hash as 16 lowercase hex characters."""
    return phash_from_grid(grid_from_bytes(image_bytes))


def average_hash_from_grid(grid: list[list[float]]) -> str:
    """aHash of the same 32x32 grid, downsampled by block mean.

    Kept as a cheap second opinion: pHash survives re-compression and mild
    crops, aHash reacts to global brightness, so agreement between the two is
    stronger evidence than either alone.
    """
    step = IMG_SIZE // HASH_SIZE
    cells = []
    for by in range(HASH_SIZE):
        for bx in range(HASH_SIZE):
            total = 0.0
            for y in range(by * step, (by + 1) * step):
                for x in range(bx * step, (bx + 1) * step):
                    total += grid[y][x]
            cells.append(total / (step * step))
    mean = sum(cells) / len(cells)
    return bits_to_hex([c > mean for c in cells])


def hash_pair_from_bytes(image_bytes: bytes) -> dict:
    """Both hashes plus basic image facts, in one decode."""
    grid = grid_from_bytes(image_bytes)
    return {
        "phash": phash_from_grid(grid),
        "ahash": average_hash_from_grid(grid),
        "hash_algorithm": "phash_dct_8x8_from_32x32_grey",
        "hash_bits": HASH_BITS,
    }


def hamming_hex(a: str, b: str) -> int | None:
    """Hamming distance between two equal-length hex hashes, else None."""
    if not a or not b:
        return None
    a, b = a.strip().lower(), b.strip().lower()
    if len(a) != len(b):
        return None
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return None


def similarity(a: str, b: str, bits: int = HASH_BITS) -> float | None:
    """1.0 identical, 0.0 fully opposite. Convenience for the UI."""
    dist = hamming_hex(a, b)
    if dist is None:
        return None
    return round(1.0 - dist / float(bits), 4)


if __name__ == "__main__":  # pragma: no cover
    if not PIL_AVAILABLE:
        raise SystemExit("Pillow not installed")
    import random

    def render(seed: int, jitter: int = 0, quality: int = 95) -> bytes:
        random.seed(seed)
        img = Image.new("RGB", (240, 240))
        px = img.load()
        blocks = [[random.randint(0, 255) for _ in range(8)] for _ in range(8)]
        for y in range(240):
            for x in range(240):
                v = blocks[y * 8 // 240][x * 8 // 240]
                v = max(0, min(255, v + jitter))
                px[x, y] = (v, v, v)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    base = generate_phash(render(7))
    recompressed = generate_phash(render(7, jitter=6, quality=40))
    different = generate_phash(render(99))
    print("base        ", base)
    print("recompressed", recompressed, "distance",
          hamming_hex(base, recompressed))
    print("different   ", different, "distance", hamming_hex(base, different))
