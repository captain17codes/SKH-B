"""Fuzzy AHP over the four criteria, with a consistency gate that can fail.

Why fuzzy AHP at all, and why it is not decoration:

The brief rules out "a fixed rule dressed up as AI". A hard-coded weight vector
is exactly that. So the weights have to come from somewhere defensible, and the
only defensible source is the people accountable for the decision -- the council's
engineers and health officers -- expressing judgements like "public safety is
somewhat more important than resource requirement". Those judgements are
linguistic, not numeric, which is why the comparisons are triangular fuzzy
numbers rather than crisp ratios.

Three properties make this auditable rather than ornamental:

* **The gate can actually fail.** Buckley's method happily produces weights from
  incoherent judgements. Saaty's consistency ratio, computed on the *crisp*
  (modal) matrix, is what detects "A > B, B > C, C > A". If CR >= 0.10 this
  module refuses to activate the weights and names the most inconsistent triple
  so the panel can revisit that one comparison instead of starting over.
* **Weights are versioned, never overwritten.** Every prioritisation run records
  which weight version produced it, so a ranking from last week can still be
  explained with the weights that were live at the time.
* **The default is declared, not hidden.** With no expert panel yet, an explicit
  seed matrix is stored as version 1 with its reasoning written into the row.
  That is a documented starting point, which is a different thing from a magic
  constant buried in the scorer.

Method: Buckley (1985) geometric mean.
  ~w_i = (prod_j ~a_ij)^(1/n),  normalised by fuzzy division:
  ~W_i = ~w_i (+) (sum_k ~w_k)^-1, using the standard interval rule that the
  lower bound of a ratio pairs the numerator's lower with the denominator's
  upper. Defuzzified by the centroid (l+m+u)/3 and renormalised to sum to 1.
Consistency: Saaty's CR = (lambda_max - n) / ((n - 1) * RI), lambda_max obtained
  by power iteration on the modal reciprocal matrix.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from domain.criteria import CRITERIA, CRITERIA_TYPES
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from domain.criteria import CRITERIA, CRITERIA_TYPES

TFN = tuple[float, float, float]

# Saaty's random-index table: the average CI of randomly generated reciprocal
# matrices of size n. Only n=4 is used today, but a fifth criterion would
# otherwise silently divide by a missing key.
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32,
                8: 1.41, 9: 1.45, 10: 1.49}

CR_THRESHOLD = 0.10

# Saaty's 1-9 scale, fuzzified: each judgement spans one step either side, which
# is the honest width of "moderately more important" as a human uses it.
LINGUISTIC_SCALE: dict[str, TFN] = {
    "equal": (1.0, 1.0, 1.0),
    "equal_to_moderate": (1.0, 2.0, 3.0),
    "moderate": (2.0, 3.0, 4.0),
    "moderate_to_strong": (3.0, 4.0, 5.0),
    "strong": (4.0, 5.0, 6.0),
    "strong_to_very_strong": (5.0, 6.0, 7.0),
    "very_strong": (6.0, 7.0, 8.0),
    "very_to_extreme": (7.0, 8.0, 9.0),
    "extreme": (8.0, 9.0, 9.0),
}

# Numeric aliases so a panel can type 3 instead of "moderate".
NUMERIC_ALIASES: dict[float, str] = {
    1: "equal", 2: "equal_to_moderate", 3: "moderate",
    4: "moderate_to_strong", 5: "strong", 6: "strong_to_very_strong",
    7: "very_strong", 8: "very_to_extreme", 9: "extreme",
}

SCALE_LABELS = tuple(LINGUISTIC_SCALE)


class InconsistentJudgements(ValueError):
    """Raised when a caller demands activation of weights that failed the gate."""


def _reciprocal(tfn: Sequence[float]) -> TFN:
    """1/~a for a positive TFN: bounds swap, because 1/x is decreasing."""
    lower, modal, upper = (float(v) for v in tfn)
    if min(lower, modal, upper) <= 0:
        raise ValueError(f"TFN must be strictly positive, got {tfn}")
    return (1.0 / upper, 1.0 / modal, 1.0 / lower)


def parse_judgement(value: Any) -> TFN:
    """Accept a label, a Saaty integer, its reciprocal, or a raw TFN triple."""
    if isinstance(value, (list, tuple)) and len(value) == 3:
        lower, modal, upper = (float(v) for v in value)
        if not (lower <= modal <= upper):
            raise ValueError(f"TFN must be ordered l <= m <= u, got {value}")
        return (lower, modal, upper)
    if isinstance(value, str):
        key = value.strip().lower().replace(" ", "_").replace("-", "_")
        inverse = key.startswith("inverse_") or key.startswith("less_")
        key = key.replace("inverse_", "").replace("less_", "")
        if key not in LINGUISTIC_SCALE:
            raise ValueError(f"unknown judgement '{value}'; "
                             f"use one of {SCALE_LABELS} or 1..9")
        tfn = LINGUISTIC_SCALE[key]
        return _reciprocal(tfn) if inverse else tfn
    number = float(value)
    if number <= 0:
        raise ValueError("a pairwise judgement must be positive")
    if number >= 1:
        nearest = min(NUMERIC_ALIASES, key=lambda k: abs(k - number))
        return LINGUISTIC_SCALE[NUMERIC_ALIASES[nearest]]
    return _reciprocal(parse_judgement(1.0 / number))


def build_matrix(judgements: dict | Iterable[dict],
                 criteria: Sequence[str] | None = None) -> list[list[TFN]]:
    """Assemble a reciprocal fuzzy matrix from the comparisons above the diagonal.

    A panel only ever states n(n-1)/2 comparisons; the rest of the matrix is
    forced by reciprocity. Deriving it here rather than asking for it removes a
    whole class of contradiction (someone entering both "A is 3x B" and "B is 2x
    A") before consistency is even measured.
    """
    names = list(criteria or CRITERIA)
    index = {name: i for i, name in enumerate(names)}
    size = len(names)
    matrix: list[list[TFN]] = [[(1.0, 1.0, 1.0) for _ in range(size)]
                               for _ in range(size)]

    pairs: list[tuple[str, str, Any]] = []
    if isinstance(judgements, dict):
        for key, value in judgements.items():
            if isinstance(key, str) and ("vs" in key or ">" in key):
                left, right = (key.replace(">", "vs").split("vs", 1))
                pairs.append((left.strip(), right.strip(), value))
            elif isinstance(key, (tuple, list)) and len(key) == 2:
                pairs.append((str(key[0]), str(key[1]), value))
            else:
                raise ValueError(f"cannot read comparison key {key!r}; "
                                 "use 'C2_safety vs C4_cost'")
    else:
        for item in judgements:
            pairs.append((str(item["a"]), str(item["b"]),
                          item.get("value", item.get("judgement"))))

    seen: set[tuple[int, int]] = set()
    for left, right, value in pairs:
        if left not in index or right not in index:
            raise ValueError(f"unknown criterion in comparison {left} vs {right}")
        i, j = index[left], index[right]
        if i == j:
            continue
        if (min(i, j), max(i, j)) in seen:
            raise ValueError(f"{left} vs {right} was given twice")
        seen.add((min(i, j), max(i, j)))
        tfn = parse_judgement(value)
        matrix[i][j] = tfn
        matrix[j][i] = _reciprocal(tfn)

    missing = [(names[i], names[j]) for i in range(size) for j in range(i + 1, size)
               if (i, j) not in seen]
    if missing:
        raise ValueError("missing comparisons: "
                         + ", ".join(f"{a} vs {b}" for a, b in missing))
    return matrix


def modal_matrix(matrix: Sequence[Sequence[Sequence[float]]]) -> list[list[float]]:
    """The crisp (most-likely) matrix. Consistency is defined on this one."""
    return [[float(cell[1]) for cell in row] for row in matrix]


def consistency(matrix: Sequence[Sequence[Sequence[float]]]) -> dict:
    """Saaty's CR on the modal matrix, plus the comparison most to blame.

    Power iteration is used for lambda_max rather than a full eigen-solver so
    this stays dependency-free (numpy may be absent on a council server).
    Convergence on a positive reciprocal matrix is guaranteed by Perron-Frobenius.
    """
    crisp = modal_matrix(matrix)
    size = len(crisp)
    if size < 3:
        return {"consistency_ratio": 0.0, "lambda_max": float(size),
                "consistency_index": 0.0, "random_index": 0.0,
                "threshold": CR_THRESHOLD, "passed": True,
                "note": "a matrix of order 2 or less cannot be inconsistent"}

    vector = [1.0 / size] * size
    lambda_max = float(size)
    for _ in range(500):
        product = [sum(crisp[i][j] * vector[j] for j in range(size))
                   for i in range(size)]
        total = sum(product)
        if total <= 0:
            break
        nxt = [v / total for v in product]
        if max(abs(a - b) for a, b in zip(nxt, vector)) < 1e-12:
            vector = nxt
            break
        vector = nxt
    # Rayleigh-style estimate: lambda_max = mean_i (Av)_i / v_i
    ratios = []
    for i in range(size):
        row_sum = sum(crisp[i][j] * vector[j] for j in range(size))
        if vector[i] > 0:
            ratios.append(row_sum / vector[i])
    if ratios:
        lambda_max = sum(ratios) / len(ratios)

    ri = RANDOM_INDEX.get(size, 1.49)
    ci = (lambda_max - size) / (size - 1)
    cr = 0.0 if ri <= 0 else ci / ri
    cr = max(0.0, cr)

    worst = _worst_triple(crisp)
    return {"consistency_ratio": round(cr, 4),
            "lambda_max": round(lambda_max, 6),
            "consistency_index": round(ci, 6),
            "random_index": ri,
            "threshold": CR_THRESHOLD,
            "passed": cr < CR_THRESHOLD,
            "priority_vector_modal": [round(v, 6) for v in vector],
            "most_inconsistent": worst,
            "method": "saaty_consistency_ratio_on_modal_matrix"}


def _worst_triple(crisp: Sequence[Sequence[float]],
                  criteria: Sequence[str] | None = None) -> dict | None:
    """The (i, j, k) whose transitivity is most violated: a_ik vs a_ij * a_jk.

    Telling a panel "your matrix is inconsistent" is useless. Telling them
    "safety > equity > cost, yet you rated cost above safety" is actionable, so
    the gate returns the single comparison worth revisiting.
    """
    names = list(criteria or CRITERIA[:len(crisp)])
    size = len(crisp)
    worst, worst_error = None, 0.0
    for i in range(size):
        for j in range(size):
            for k in range(size):
                if len({i, j, k}) < 3:
                    continue
                implied = crisp[i][j] * crisp[j][k]
                stated = crisp[i][k]
                if stated <= 0 or implied <= 0:
                    continue
                error = abs(math.log(stated / implied))
                if error > worst_error:
                    worst_error = error
                    worst = {"stated": f"{names[i]} vs {names[k]}",
                             "stated_value": round(stated, 4),
                             "implied_via": names[j],
                             "implied_value": round(implied, 4),
                             "log_discrepancy": round(error, 4)}
    return worst


def buckley_weights(matrix: Sequence[Sequence[Sequence[float]]],
                    criteria: Sequence[str] | None = None) -> dict:
    """Fuzzy weights by geometric mean, then centroid defuzzification.

    The fuzzy weight is kept alongside the crisp one on purpose: the crisp vector
    is what TOPSIS multiplies, and the fuzzy vector is what lets an explanation
    say how wide the panel's own uncertainty about that weight was.
    """
    names = list(criteria or CRITERIA[:len(matrix)])
    size = len(matrix)
    geo: list[TFN] = []
    for row in matrix:
        lower = math.prod(float(cell[0]) for cell in row) ** (1.0 / size)
        modal = math.prod(float(cell[1]) for cell in row) ** (1.0 / size)
        upper = math.prod(float(cell[2]) for cell in row) ** (1.0 / size)
        geo.append((lower, modal, upper))

    sum_lower = sum(g[0] for g in geo)
    sum_modal = sum(g[1] for g in geo)
    sum_upper = sum(g[2] for g in geo)

    fuzzy: dict[str, list[float]] = {}
    for name, g in zip(names, geo):
        # Fuzzy division: pair the numerator's lower bound with the denominator's
        # upper bound, which is what makes the interval a genuine bound rather
        # than an optimistic point estimate.
        fuzzy[name] = [round(g[0] / sum_upper, 6),
                       round(g[1] / sum_modal, 6),
                       round(g[2] / sum_lower, 6)]

    centroids = {name: sum(fuzzy[name]) / 3.0 for name in names}
    total = sum(centroids.values()) or 1.0
    crisp = {name: round(centroids[name] / total, 6) for name in names}
    # Absorb rounding drift into the largest weight so the vector sums to 1.0.
    drift = round(1.0 - sum(crisp.values()), 6)
    if abs(drift) >= 1e-6:
        heaviest = max(crisp, key=lambda k: crisp[k])
        crisp[heaviest] = round(crisp[heaviest] + drift, 6)

    return {"criteria": names,
            "geometric_means": {n: [round(v, 6) for v in g]
                                for n, g in zip(names, geo)},
            "fuzzy_weights": fuzzy,
            "crisp_weights": crisp,
            "method": "buckley_geometric_mean_centroid_defuzzified"}


def derive(judgements: dict | Iterable[dict] | None = None,
           matrix: Sequence[Sequence[Sequence[float]]] | None = None,
           criteria: Sequence[str] | None = None) -> dict:
    """Full pipeline: judgements -> matrix -> weights + consistency verdict.

    Weights are returned even when the gate fails. Hiding them would stop the
    panel from seeing *how* the inconsistency distorts the result, and the caller
    still cannot activate a failed set -- that refusal lives in the weight
    service, not here.
    """
    names = list(criteria or CRITERIA)
    if matrix is None:
        if judgements is None:
            raise ValueError("supply either judgements or a matrix")
        matrix = build_matrix(judgements, names)
    check = consistency(matrix)
    weights = buckley_weights(matrix, names)
    if len(names) >= 3:
        check["most_inconsistent"] = _worst_triple(modal_matrix(matrix), names)
    return {
        "criteria": names,
        "criteria_types": [CRITERIA_TYPES.get(n, "benefit") for n in names],
        "pairwise_matrix": [[list(cell) for cell in row] for row in matrix],
        "fuzzy_weights": weights["fuzzy_weights"],
        "crisp_weights": weights["crisp_weights"],
        "geometric_means": weights["geometric_means"],
        "consistency": check,
        "cr_passed": bool(check["passed"]),
        "method": weights["method"],
    }


# The declared starting point, used only until a real panel sits down.
#
# Reasoning, recorded so it can be challenged rather than inherited:
#   * safety above infrastructure -- a live electrical fault outranks a pothole
#     on the same road, and the council's own priority floors say so;
#   * infrastructure above equity -- equity is currently unmeasurable for
#     Kopargaon (no ward data), so leaning on it would weight a guess;
#   * cost lowest and it is a *cost* criterion, so a cheap fix is favoured only
#     after need is established, never instead of it.
DEFAULT_JUDGEMENTS: dict[str, Any] = {
    "C2_safety vs C1_infra": "equal_to_moderate",
    "C2_safety vs C3_equity": "moderate",
    "C2_safety vs C4_cost": "moderate_to_strong",
    "C1_infra vs C3_equity": "equal_to_moderate",
    "C1_infra vs C4_cost": "moderate",
    "C3_equity vs C4_cost": "equal_to_moderate",
}

DEFAULT_NOTE = (
    "Seed weights, not an expert elicitation. Derived from the council's own "
    "published priority floors (safety-first) and from the fact that no ward "
    "equity data exists yet, so equity must not dominate. Replace via "
    "POST /api/weights/derive once the engineering and health panel has met."
)


def default_derivation() -> dict:
    out = derive(DEFAULT_JUDGEMENTS)
    out["label"] = "seed_v1_published_priority_floors"
    out["note"] = DEFAULT_NOTE
    out["is_seed"] = True
    return out


if __name__ == "__main__":  # pragma: no cover
    import json

    base = default_derivation()
    print("seed weights   :", json.dumps(base["crisp_weights"]))
    print("fuzzy C2       :", base["fuzzy_weights"]["C2_safety"])
    print("CR             :", base["consistency"]["consistency_ratio"],
          "passed" if base["cr_passed"] else "FAILED")
    print("sum            :", round(sum(base["crisp_weights"].values()), 6))

    # A deliberately circular panel: safety > equity > cost > safety.
    circular = dict(DEFAULT_JUDGEMENTS)
    circular["C3_equity vs C4_cost"] = "very_strong"
    circular["C2_safety vs C4_cost"] = "inverse_strong"
    bad = derive(circular)
    print("circular CR    :", bad["consistency"]["consistency_ratio"],
          "passed" if bad["cr_passed"] else "FAILED")
    print("blame          :", json.dumps(bad["consistency"]["most_inconsistent"]))

    # Perfectly consistent matrix must give CR ~ 0.
    ideal = {"C2_safety vs C1_infra": 2, "C1_infra vs C3_equity": 2,
             "C3_equity vs C4_cost": 2, "C2_safety vs C3_equity": 4,
             "C1_infra vs C4_cost": 4, "C2_safety vs C4_cost": 8}
    perfect = derive(ideal)
    print("ideal CR       :", perfect["consistency"]["consistency_ratio"])
    print("ideal weights  :", json.dumps(perfect["crisp_weights"]))
    print("equal weights  :", json.dumps(derive(
        {f"{a} vs {b}": "equal" for i, a in enumerate(CRITERIA)
         for b in CRITERIA[i + 1:]})["crisp_weights"]))
