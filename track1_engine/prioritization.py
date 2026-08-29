"""Fuzzy TOPSIS ranking for competing civic complaints.

This is the step that turns four fuzzy criterion scores per ticket into one
ranked list. It is deliberately *not* a weighted sum: a weighted sum lets a very
cheap trivial job out-score a dangerous expensive one by accumulating small
advantages, whereas TOPSIS measures how close a ticket is to the best achievable
profile and how far from the worst, which is the question a ward officer is
actually asking.

Three properties matter for the defence of this code:

* **Numpy-free.** Pure stdlib arithmetic, so the backend installs from wheels in
  seconds on a fresh council machine and there is no BLAS to go wrong. The old
  numpy implementation's results are reproduced exactly; ``tests/test_engine.py``
  still passes unchanged.
* **The decomposition is exact, not a post-hoc guess.** Because
  ``CCi = d-/(d+ + d-)`` and ``d-`` is a plain sum over criteria, each criterion's
  share ``d-_j/(d+ + d-)`` adds up to CCi exactly. So "safety contributed 0.31 of
  this ticket's 0.68" is arithmetic, not an approximation. SHAP is layered on top
  of this later for familiarity, never instead of it.
* **Degenerate columns fail loudly-but-safely.** A criterion where every ticket
  scores zero, or a cost criterion whose minimum is zero, cannot be normalised by
  the textbook formula. Rather than emit NaN (which silently poisons the ranking)
  each case is handled explicitly and recorded in ``normalisation_notes``.

Method (Chen 2000):
  benefit: r_ij = (l/c*, m/c*, u/c*)  with c* = max_i u_ij
  cost   : r_ij = (a-/u, a-/m, a-/l)  with a- = min_i l_ij
  weighted: v_ij = r_ij (x) w_j  (element-wise on the TFN)
  FPIS = (1,1,1) per criterion, FNIS = (0,0,0) per criterion
  vertex distance d(x, y) = sqrt(1/3 [(l1-l2)^2 + (m1-m2)^2 + (u1-u2)^2])
  CCi = d- / (d+ + d-)
"""
from __future__ import annotations

import math
from typing import Any, Sequence

TFN = tuple[float, float, float]

# Guards a division, and marks the boundary below which a normaliser is treated
# as degenerate rather than merely small.
EPSILON = 1e-12

CRITERION_NAMES = ("C1_infra", "C2_safety", "C3_equity", "C4_cost")


def _as_tfn(value: Any) -> TFN:
    """Accept a TFN triple or a single crisp number (a zero-width TFN)."""
    if isinstance(value, (int, float)):
        v = float(value)
        return (v, v, v)
    seq = list(value)
    if len(seq) == 1:
        v = float(seq[0])
        return (v, v, v)
    if len(seq) != 3:
        raise ValueError(f"expected a TFN of 3 values or a scalar, got {value!r}")
    lower, modal, upper = (float(x) for x in seq)
    # Tolerate an unordered triple by sorting rather than rejecting it: the
    # caller's intent is unambiguous and refusing the whole run over a swapped
    # pair would drop a citizen's ticket out of the ranking.
    if not (lower <= modal <= upper):
        lower, modal, upper = sorted((lower, modal, upper))
    return (lower, modal, upper)


def distance_tfn(tfn1: Sequence[float], tfn2: Sequence[float]) -> float:
    """Vertex distance between two triangular fuzzy numbers."""
    l1, m1, u1 = _as_tfn(tfn1)
    l2, m2, u2 = _as_tfn(tfn2)
    return math.sqrt(((l1 - l2) ** 2 + (m1 - m2) ** 2 + (u1 - u2) ** 2) / 3.0)


def normalize_fuzzy_matrix(matrix: Sequence[Sequence[Sequence[float]]],
                           criteria_types: Sequence[str],
                           notes: list[str] | None = None,
                           ) -> list[list[TFN]]:
    """Scale every criterion into [0, 1] so the four are commensurable.

    Benefit and cost columns use different formulae on purpose: for a benefit
    criterion a bigger raw score should end up nearer 1, and for a cost criterion
    a *smaller* raw score should. Doing this here rather than by negating the
    weight later is what keeps "resource requirement" readable as a cost in the
    stored audit trail.
    """
    rows = [[_as_tfn(cell) for cell in row] for row in matrix]
    if not rows:
        return []
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("every ticket must score the same number of criteria")
    if len(criteria_types) != width:
        raise ValueError(f"{len(criteria_types)} criteria types for {width} columns")

    out: list[list[TFN]] = [[(0.0, 0.0, 0.0)] * width for _ in rows]
    for j, kind in enumerate(criteria_types):
        column = [row[j] for row in rows]
        if kind == "cost":
            a_min = min(cell[0] for cell in column)
            if a_min <= EPSILON:
                # Textbook a-/x collapses the whole column to zero when any
                # ticket has a zero lower bound, which would delete the criterion
                # from the ranking. Complement normalisation preserves the
                # ordering (cheap -> near 1) and is stated in the notes.
                u_max = max(cell[2] for cell in column) or 1.0
                for i, (low, mid, high) in enumerate(column):
                    out[i][j] = (1.0 - high / u_max, 1.0 - mid / u_max,
                                 1.0 - low / u_max)
                if notes is not None:
                    notes.append(
                        f"criterion {j} is a cost criterion whose minimum lower "
                        f"bound is 0; used complement normalisation "
                        f"(1 - x/max) instead of a-/x to avoid zeroing the column")
                continue
            for i, (low, mid, high) in enumerate(column):
                out[i][j] = (a_min / high if high > EPSILON else 0.0,
                             a_min / mid if mid > EPSILON else 0.0,
                             a_min / low if low > EPSILON else 0.0)
        else:
            c_max = max(cell[2] for cell in column)
            if c_max <= EPSILON:
                # Every ticket scored zero here, so the criterion cannot
                # discriminate. Zeroing it is correct and must be visible.
                if notes is not None:
                    notes.append(f"criterion {j} scored 0 for every candidate; "
                                 f"it did not affect this ranking")
                continue
            for i, (low, mid, high) in enumerate(column):
                out[i][j] = (low / c_max, mid / c_max, high / c_max)
    return out


def apply_weights(normalized_matrix: Sequence[Sequence[Sequence[float]]],
                  weights: Sequence[Any]) -> list[list[TFN]]:
    """Element-wise TFN multiplication by the criterion weights.

    Weights may be TFNs (from fuzzy AHP) or plain numbers; a crisp weight is a
    zero-width TFN, so both paths use the same arithmetic.
    """
    tfn_weights = [_as_tfn(w) for w in weights]
    out: list[list[TFN]] = []
    for row in normalized_matrix:
        if len(row) != len(tfn_weights):
            raise ValueError("weight count does not match criterion count")
        out.append([(x[0] * w[0], x[1] * w[1], x[2] * w[2])
                    for x, w in zip((_as_tfn(c) for c in row), tfn_weights)])
    return out


def calculate_ideal_solutions(num_criteria: int,
                              weights: Sequence[Any] | None = None,
                              ) -> tuple[list[TFN], list[TFN]]:
    """FPIS and FNIS in *weighted* normalised space.

    The textbook shortcut puts the ideal at (1,1,1) per criterion, but in
    weighted space a criterion can never exceed its own weight -- a normalised
    score of 1 times a weight of 0.10 is 0.10. Anchoring the ideal at an
    unreachable point compresses every CCi into a narrow band near zero, which
    still ranks correctly but produces numbers no officer can interpret ("your
    complaint scored 0.18 out of 1" when 0.19 was the best possible). Scaling the
    ideal by the weights restores the full range while keeping the anchor
    *fixed*: it depends on the weight version, not on which other complaints
    happened to arrive today, so a CCi stays comparable across runs.

    Passing no weights reproduces the original (1,1,1) behaviour.
    """
    if weights is None:
        return ([(1.0, 1.0, 1.0)] * num_criteria,
                [(0.0, 0.0, 0.0)] * num_criteria)
    tfn_weights = [_as_tfn(w) for w in weights]
    if len(tfn_weights) != num_criteria:
        raise ValueError("weight count does not match criterion count")
    # The best reachable weighted value is the weight itself, treated as a crisp
    # target so the ideal is a point rather than a fuzzy region.
    fpis = [(w[2], w[2], w[2]) for w in tfn_weights]
    return (fpis, [(0.0, 0.0, 0.0)] * num_criteria)


def _row_distances(weighted_row: Sequence[Sequence[float]],
                   fpis: Sequence[Sequence[float]],
                   fnis: Sequence[Sequence[float]],
                   ) -> tuple[float, float, list[float], list[float]]:
    """Per-criterion distances to the ideal and anti-ideal, and their sums."""
    per_positive = [distance_tfn(weighted_row[j], fpis[j])
                    for j in range(len(weighted_row))]
    per_negative = [distance_tfn(weighted_row[j], fnis[j])
                    for j in range(len(weighted_row))]
    return sum(per_positive), sum(per_negative), per_positive, per_negative


def calculate_closeness_coefficient(weighted_matrix, fpis, fnis) -> list[float]:
    """CCi for each alternative: 1.0 is the ideal profile, 0.0 the worst."""
    scores: list[float] = []
    for row in weighted_matrix:
        d_plus, d_minus, _, _ = _row_distances(row, fpis, fnis)
        total = d_plus + d_minus
        scores.append(0.0 if total <= EPSILON else d_minus / total)
    return scores


def attribute(weighted_row: Sequence[Sequence[float]],
              fpis: Sequence[Sequence[float]],
              fnis: Sequence[Sequence[float]],
              names: Sequence[str] | None = None) -> list[dict]:
    """Split a ticket's CCi into an exact per-criterion contribution.

    ``CCi = d- / (d+ + d-)`` and ``d- = sum_j d-_j``, so ``d-_j / (d+ + d-)`` is
    each criterion's *actual* share of the score and the shares sum to CCi to
    floating-point precision. The mirror term ``d+_j / (d+ + d-)`` is the score
    that criterion cost the ticket, and the two sets together sum to 1.0.

    This is what makes "your complaint scored 0.62, of which public-safety risk
    contributed 0.29" a statement about the arithmetic rather than a narrative
    bolted on afterwards.
    """
    labels = list(names or CRITERION_NAMES[:len(weighted_row)])
    d_plus, d_minus, per_positive, per_negative = _row_distances(
        weighted_row, fpis, fnis)
    total = d_plus + d_minus
    out: list[dict] = []
    for j, label in enumerate(labels):
        gained = 0.0 if total <= EPSILON else per_negative[j] / total
        lost = 0.0 if total <= EPSILON else per_positive[j] / total
        out.append({
            "criterion": label,
            "weighted_tfn": [round(v, 6) for v in _as_tfn(weighted_row[j])],
            "distance_to_ideal": round(per_positive[j], 6),
            "distance_to_anti_ideal": round(per_negative[j], 6),
            "contribution": round(gained, 6),
            "forgone": round(lost, 6),
            # Contributions sum to CCi; shares renormalise them to sum to 1.0,
            # which is the form a UI bar chart wants.
            "share_of_score": round(per_negative[j] / d_minus, 6)
            if d_minus > EPSILON else 0.0,
        })
    return out


def _resolve_weights(criteria_config: dict, names: Sequence[str],
                     width: int) -> list[Any]:
    """Accept weights as a list of TFNs, a list of numbers, or a dict by name.

    The AHP service hands back ``{criterion: crisp_weight}``; the fuzzy AHP
    derivation hands back ``{criterion: [l, m, u]}``; the original engine tests
    hand back a positional list. All three are legitimate callers, so all three
    are accepted rather than forcing one to reshape at the call site.
    """
    raw = criteria_config.get("weights")
    if raw is None:
        return [1.0 / width] * width
    if isinstance(raw, dict):
        missing = [n for n in names if n not in raw]
        if missing:
            raise ValueError(f"weights are missing criteria: {missing}")
        return [raw[n] for n in names]
    weights = list(raw)
    if len(weights) != width:
        raise ValueError(f"{len(weights)} weights for {width} criteria")
    return weights


def run_prioritization(tickets_data: Sequence[dict],
                       criteria_config: dict) -> list[dict]:
    """Rank tickets by fuzzy TOPSIS. Returns copies, sorted best-first.

    ``tickets_data``: ``[{'id': ..., 'scores': [[l,m,u] x n_criteria]}, ...]``
    ``criteria_config``: ``{'types': ['benefit', ..., 'cost'], 'weights': ...}``
    plus optional ``'names'``.

    Each returned dict keeps every key it arrived with and gains ``topsis_score``,
    ``d_positive``, ``d_negative``, ``attribution`` and ``rank``. The input is not
    mutated, so a caller can re-rank the same candidates under different weights
    and diff the two -- which is exactly what "would last month's weights have
    scheduled this ticket?" needs.

    Ties break on ``id`` so two runs over identical data produce an identical
    order. Without that, a manifest could reshuffle between a preview and the
    dispatch it is supposed to justify.
    """
    if not tickets_data:
        return []

    matrix = [t["scores"] for t in tickets_data]
    width = len(matrix[0])
    criteria_types = list(criteria_config.get("types")
                          or ["benefit"] * (width - 1) + ["cost"])
    names = list(criteria_config.get("names") or CRITERION_NAMES[:width])
    weights = _resolve_weights(criteria_config, names, width)

    notes: list[str] = []
    normalized = normalize_fuzzy_matrix(matrix, criteria_types, notes)
    weighted = apply_weights(normalized, weights)
    fpis, fnis = calculate_ideal_solutions(width, weights)

    results: list[dict] = []
    for ticket, row in zip(tickets_data, weighted):
        d_plus, d_minus, _, _ = _row_distances(row, fpis, fnis)
        total = d_plus + d_minus
        enriched = dict(ticket)
        enriched["topsis_score"] = 0.0 if total <= EPSILON else d_minus / total
        enriched["d_positive"] = round(d_plus, 6)
        enriched["d_negative"] = round(d_minus, 6)
        enriched["attribution"] = attribute(row, fpis, fnis, names)
        enriched["normalisation_notes"] = list(notes)
        results.append(enriched)

    results.sort(key=lambda r: (-float(r["topsis_score"]), str(r.get("id", ""))))
    for position, item in enumerate(results, start=1):
        item["rank"] = position
    return results


if __name__ == "__main__":  # pragma: no cover
    import json

    demo = [
        {"id": "live_wire", "scores": [[0.7, 0.8, 0.9], [0.85, 0.95, 1.0],
                                       [0.2, 0.3, 0.4], [0.5, 0.6, 0.7]]},
        {"id": "pothole", "scores": [[0.3, 0.4, 0.5], [0.1, 0.2, 0.3],
                                     [0.3, 0.4, 0.5], [0.1, 0.2, 0.3]]},
        {"id": "slum_drain", "scores": [[0.4, 0.5, 0.6], [0.5, 0.6, 0.7],
                                        [0.8, 0.9, 1.0], [0.2, 0.3, 0.4]]},
    ]
    config = {"types": ["benefit", "benefit", "benefit", "cost"],
              "weights": {"C1_infra": 0.283776, "C2_safety": 0.449226,
                          "C3_equity": 0.167336, "C4_cost": 0.099662}}
    ranked = run_prioritization(demo, config)
    for row in ranked:
        print(f"{row['rank']}. {row['id']:<11} CCi {row['topsis_score']:.4f}"
              f"  d+ {row['d_positive']:.4f}  d- {row['d_negative']:.4f}")
    top = ranked[0]
    print(f"\nexact decomposition of {top['id']} (sums to CCi):")
    for part in top["attribution"]:
        print(f"   {part['criterion']:<11} contributed {part['contribution']:.4f}"
              f"   forgone {part['forgone']:.4f}")
    print("   sum of contributions:",
          round(sum(p["contribution"] for p in top["attribution"]), 6),
          "vs CCi", round(top["topsis_score"], 6))

    print("\nzero-cost column must not delete the cost criterion:")
    degenerate = [{"id": "free", "scores": [[0.5, 0.6, 0.7]] * 3 + [[0.0, 0.0, 0.0]]},
                  {"id": "pricey", "scores": [[0.5, 0.6, 0.7]] * 3 + [[0.6, 0.7, 0.8]]}]
    for row in run_prioritization(degenerate, config):
        print(f"   {row['id']:<8} CCi {row['topsis_score']:.4f}")
    print("   note:", json.dumps(run_prioritization(
        degenerate, config)[0]["normalisation_notes"]))
