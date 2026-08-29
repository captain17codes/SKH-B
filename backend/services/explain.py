"""Why this ticket, in a citizen's words and in an officer's numbers.

The hackathon brief has two halves and most entries only build the first. Deciding
which complaints get today's crew is the algorithm; **telling the affected citizen
what was decided and why** is the other half, and a queue position with no reason
attached is exactly what makes people stop trusting the queue.

Everything here is derived from what the run already recorded. Nothing is
re-computed and nothing is invented:

* **The primary explanation is exact arithmetic, not a model of a model.** Because
  ``CCi = d-/(d+ + d-)`` and ``d-`` is a plain sum over the four criteria, each
  criterion's share ``d-_j/(d+ + d-)`` adds up to CCi exactly. So "public-safety
  risk contributed 0.29 of your 0.62" is a statement about the calculation, not an
  approximation of it. That is stored per run in
  ``ticket_scores.criteria_snapshot`` and simply read back here.
* **SHAP is offered as a familiar second opinion, never as the explanation.** A
  surrogate forest fitted on one day's cohort can only approximate the ranking it
  was fitted to, and the council has no historical resolution dataset to fit
  anything better. It is therefore optional, clearly labelled as a surrogate, and
  reported with its own fidelity (R^2) so a reader can see how much to trust it.
  If ``scikit-learn``/``shap`` are not installed the endpoint still works.
* **The decision explanation is separate from the score explanation.** A ticket
  can rank second and still not be scheduled -- because nobody has costed it, or
  because the same rupees bought more work elsewhere. Those are different
  sentences with different next steps, and conflating them is how "deferred"
  becomes indistinguishable from "ignored".
* **Marathi is drafted, not claimed as reviewed.** Kopargaon is a Marathi-speaking
  council, so an English-only notification is a real accessibility failure. The
  datasets contain no approved Marathi templates, so the translation is generated
  here and stamped ``machine_drafted_pending_council_review`` rather than passed
  off as official copy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

if __name__ == "__main__":  # pragma: no cover
    # The self-test must never touch working data, and the database path is read
    # once when ``config`` is imported -- so the redirect has to happen before the
    # first-party imports below, not in the test block at the bottom.
    import os
    import shutil
    import tempfile

    _SCRATCH = Path(tempfile.gettempdir()) / "crpp_explain_selftest"
    shutil.rmtree(_SCRATCH, ignore_errors=True)
    (_SCRATCH / "uploads").mkdir(parents=True, exist_ok=True)
    os.environ["CRPP_DB_PATH"] = str(_SCRATCH / "selftest.db")
    os.environ["UPLOAD_DIR"] = str(_SCRATCH / "uploads")

try:
    from config import settings
    from database import dumps, insert, loads, new_id, query_all, query_one, \
        utcnow_iso
    from domain.criteria import CRITERIA
    from services import audit
    from services import tickets as ticket_service
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from config import settings
    from database import dumps, insert, loads, new_id, query_all, query_one, \
        utcnow_iso
    from domain.criteria import CRITERIA
    from services import audit
    from services import tickets as ticket_service

METHOD_EXACT = "topsis_exact_decomposition"
METHOD_SHAP = "shap_surrogate_on_current_cohort"
TRANSLATION_STATUS = "machine_drafted_pending_council_review"

# Two vocabularies per criterion. The short label is what a dashboard column
# header needs; the ``citizen`` phrasing is what a person who never asked for a
# multi-criteria decision model needs, and it names the *thing measured* rather
# than the criterion code.
CRITERION_LABELS: dict[str, dict[str, str]] = {
    "C1_infra": {
        "en": "infrastructural criticality",
        "mr": "पायाभूत सुविधांची निकड",
        "citizen_en": "how quickly the council's own service standard says this "
                      "kind of fault must be answered",
        "citizen_mr": "अशा प्रकारच्या तक्रारीला नगरपालिकेच्या सेवा मानकानुसार "
                      "किती लवकर उत्तर द्यावे लागते",
    },
    "C2_safety": {
        "en": "public safety and health risk",
        "mr": "सार्वजनिक सुरक्षा व आरोग्य धोका",
        "citizen_en": "the danger it poses to people's safety and health",
        "citizen_mr": "लोकांच्या सुरक्षेला व आरोग्याला असलेला धोका",
    },
    "C3_equity": {
        "en": "socio-spatial equity",
        "mr": "सामाजिक व भौगोलिक समानता",
        "citizen_en": "how much service your area has had compared with the "
                      "rest of the town",
        "citizen_mr": "शहराच्या इतर भागांच्या तुलनेत तुमच्या भागाला मिळालेली सेवा",
    },
    "C4_cost": {
        "en": "resource requirement",
        "mr": "आवश्यक संसाधने",
        "citizen_en": "how much crew time and money the repair needs",
        "citizen_mr": "दुरुस्तीसाठी लागणारा कर्मचारी वेळ व खर्च",
    },
}

# What the citizen is told, keyed by the allocator's reason code. Each entry
# carries the outcome sentence and -- more importantly -- what happens next, so
# the message is actionable rather than merely polite.
CITIZEN_TEMPLATES: dict[str, dict[str, str]] = {
    "allocated": {
        "en": "Your complaint {ref} has been scheduled for work on {date}. It "
              "ranked {rank} of {total} complaints considered today, mainly "
              "because of {driver}.",
        "mr": "तुमची तक्रार {ref} {date} रोजी कामासाठी नियोजित करण्यात आली आहे. "
              "आज विचारात घेतलेल्या {total} तक्रारींमध्ये ती {rank} क्रमांकावर "
              "होती, मुख्यतः {driver} यामुळे.",
        "next_en": "A crew is assigned for that date. You will be told again "
                   "when the work is closed.",
        "next_mr": "त्या दिवसासाठी पथक नेमले आहे. काम पूर्ण झाल्यावर तुम्हाला "
                   "पुन्हा कळवले जाईल.",
        # Used only when a higher-ranked complaint was held back while this one
        # went ahead. Saying nothing here is what makes an allocation look
        # arbitrary: a citizen who knows a worse-scoring job was done first is
        # owed the reason, which is that the day is packed by combination and
        # not by walking down the list.
        "fit_en": "Complaints are not simply taken in rank order: the day's "
                  "budget and crew hours are filled with the combination that "
                  "addresses the most, and this one fitted the hours and money "
                  "that were left.",
        "fit_mr": "तक्रारी केवळ क्रमांकानुसार घेतल्या जात नाहीत: दिवसाचा "
                  "अर्थसंकल्प व मनुष्यबळ ज्या संयोजनाने सर्वाधिक काम होईल त्याने "
                  "भरले जाते, आणि उरलेल्या वेळेत व निधीत ही तक्रार बसली.",
    },
    "allocated_mandatory_floor": {
        "en": "Your complaint {ref} has been taken up for {date} without waiting "
              "for the daily comparison: {driver} places it in the council's "
              "non-negotiable safety category.",
        "mr": "तुमची तक्रार {ref} दैनंदिन तुलनेची वाट न पाहता {date} साठी "
              "हाती घेतली आहे: {driver} यामुळे ती नगरपालिकेच्या अनिवार्य "
              "सुरक्षा गटात येते.",
        "next_en": "This category is committed before any budget comparison is "
                   "made. A crew is assigned for that date.",
        "next_mr": "हा गट अर्थसंकल्पीय तुलनेच्या आधीच निश्चित केला जातो. त्या "
                   "दिवसासाठी पथक नेमले आहे.",
    },
    "deferred_cost_not_estimated": {
        "en": "Your complaint {ref} ranked {rank} of {total} today, mainly "
              "because of {driver}, but it could not be put on {date}'s work "
              "list yet: nobody has estimated what the repair will cost.",
        "mr": "तुमची तक्रार {ref} आज {total} पैकी {rank} क्रमांकावर होती, "
              "मुख्यतः {driver} यामुळे; परंतु दुरुस्तीचा खर्च अद्याप ठरलेला "
              "नसल्याने ती {date} च्या कामाच्या यादीत घेता आली नाही.",
        "next_en": "It keeps this rank. Once an engineer records the cost it is "
                   "scheduled at the next run, without you having to report it "
                   "again.",
        "next_mr": "तिचा क्रमांक कायम राहील. अभियंत्याने खर्च नोंदवल्यानंतर "
                   "पुढील नियोजनात ती घेतली जाईल; तुम्हाला पुन्हा तक्रार "
                   "करण्याची गरज नाही.",
    },
    "deferred_exceeds_daily_capacity": {
        "en": "Your complaint {ref} ranked {rank} of {total} today, mainly "
              "because of {driver}. It needs more than one day's entire budget "
              "or crew, so it cannot be done in a single day's work list.",
        "mr": "तुमची तक्रार {ref} आज {total} पैकी {rank} क्रमांकावर होती, "
              "मुख्यतः {driver} यामुळे. या कामासाठी एका दिवसाच्या संपूर्ण "
              "अर्थसंकल्पापेक्षा किंवा मनुष्यबळापेक्षा जास्त गरज आहे, म्हणून "
              "ते एका दिवसात करता येणार नाही.",
        "next_en": "It has been flagged for a multi-day plan or a separate "
                   "allocation rather than left in the daily queue.",
        "next_mr": "ती दैनंदिन रांगेत ठेवण्याऐवजी बहु-दिवसीय नियोजन किंवा "
                   "स्वतंत्र निधीसाठी नोंदवली आहे.",
    },
    "deferred_capacity_used_by_higher_value_set": {
        "en": "Your complaint {ref} ranked {rank} of {total} today, mainly "
              "because of {driver}. It fits within {date}'s budget on its own, "
              "but the same money and crew hours covered a combination of "
              "higher-priority work.",
        "mr": "तुमची तक्रार {ref} आज {total} पैकी {rank} क्रमांकावर होती, "
              "मुख्यतः {driver} यामुळे. एकटी असता ती {date} च्या "
              "अर्थसंकल्पात बसते, परंतु तोच निधी व मनुष्यबळ अधिक "
              "प्राधान्याच्या कामांच्या संचासाठी वापरला गेला.",
        "next_en": "It carries forward automatically and its position improves "
                   "as its deadline approaches.",
        "next_mr": "ती स्वयंचलितपणे पुढे नेली जाते आणि मुदत जवळ येईल तसा तिचा "
                   "क्रमांक सुधारतो.",
    },
}

def _ordinal(n: Any) -> str:
    """1 -> '1st'. Used in citizen text, where 'rank 3' reads like jargon."""
    try:
        value = int(n)
    except (TypeError, ValueError):
        return "unranked"
    if 10 <= value % 100 <= 20:
        return f"{value}th"
    return f"{value}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(value % 10, 'th') }"


def _score_row(conn, ticket_id: str, run_id: str | None = None) -> dict | None:
    """The stored score for a ticket, newest run unless one is named.

    Reading the stored row rather than re-ranking is the whole point: an
    explanation must describe the decision that was actually taken, under the
    weights that were actually in force, even after the weights change.
    """
    if run_id:
        return query_one(conn, "SELECT * FROM ticket_scores WHERE ticket_id = ? "
                               "AND run_id = ?", (ticket_id, run_id))
    return query_one(conn, "SELECT * FROM ticket_scores WHERE ticket_id = ? "
                           "ORDER BY created_at DESC, rowid DESC LIMIT 1",
                     (ticket_id,))


def _decision_row(conn, ticket_id: str, run_id: str) -> dict | None:
    """The manifest line for this ticket in this run, with the run's context."""
    return query_one(conn,
                     "SELECT i.*, m.dispatch_date, m.budget_available, "
                     "m.workforce_available, m.budget_used, m.workforce_used, "
                     "m.allocated_count, m.deferred_count, m.total_candidates, "
                     "m.solver, m.budget_outcome, m.weight_version, m.notes, "
                     "m.id AS manifest_id "
                     "FROM dispatch_manifest_items i "
                     "JOIN dispatch_manifests m ON m.id = i.manifest_id "
                     "WHERE i.ticket_id = ? AND m.run_id = ?",
                     (ticket_id, run_id))


def _rivals(conn, manifest_id: str, ticket_id: str, limit: int = 5) -> list[dict]:
    """What the same rupees and hours bought instead.

    This is the answer to the only question a deferred citizen actually asks. A
    reason code says "outbid"; this says by what, at what score, for what money --
    which is the difference between a decision that can be argued with and one
    that can only be accepted.
    """
    rows = query_all(conn,
                     "SELECT i.ticket_id, i.rank_position, i.cci, i.cost_inr, "
                     "i.hours, t.category, t.ref_no, t.ward_id "
                     "FROM dispatch_manifest_items i "
                     "JOIN tickets t ON t.id = i.ticket_id "
                     "WHERE i.manifest_id = ? AND i.decision = 'allocated' "
                     "AND i.ticket_id != ? "
                     "ORDER BY i.rank_position LIMIT ?",
                     (manifest_id, ticket_id, int(limit)))
    return [{"ticket_id": r["ticket_id"], "ref_no": r["ref_no"],
             "category": r["category"], "ward_id": r["ward_id"],
             "rank": r["rank_position"], "cci_score": r["cci"],
             "cost_inr": r["cost_inr"], "hours": r["hours"]} for r in rows]


def _better_ranked_deferred(conn, manifest_id: str, rank: Any) -> int:
    """How many higher-ranked complaints were held back while this one went ahead.

    Non-zero is the signature of the knapsack doing real work, and it is the one
    fact that makes an allocation message look wrong if left out.
    """
    if rank is None:
        return 0
    row = query_one(conn,
                    "SELECT COUNT(*) AS n FROM dispatch_manifest_items "
                    "WHERE manifest_id = ? AND decision != 'allocated' "
                    "AND rank_position < ?", (manifest_id, int(rank)))
    return int(row["n"]) if row else 0

def shape_attribution(attribution: Sequence[dict], cci_base: float) -> dict:
    """Rank the four criteria by what they actually contributed, with labels.

    ``share_of_score`` renormalises the contributions to sum to 1.0, which is what
    a bar chart wants; ``contribution`` keeps the raw share of CCi, which is what
    the arithmetic check wants. Both are returned because dropping either forces
    the reader to trust a conversion they cannot see.
    """
    rows: list[dict] = []
    for part in attribution or []:
        code = part.get("criterion")
        labels = CRITERION_LABELS.get(code, {})
        rows.append({
            "criterion": code,
            "label": labels.get("en", code),
            "label_mr": labels.get("mr"),
            "plain_language": labels.get("citizen_en"),
            "plain_language_mr": labels.get("citizen_mr"),
            "contribution": part.get("contribution"),
            "forgone": part.get("forgone"),
            "share_of_score": part.get("share_of_score"),
            "weighted_tfn": part.get("weighted_tfn"),
            "distance_to_ideal": part.get("distance_to_ideal"),
            "distance_to_anti_ideal": part.get("distance_to_anti_ideal"),
        })
    rows.sort(key=lambda r: -(r["contribution"] or 0.0))
    total = sum(r["contribution"] or 0.0 for r in rows)
    return {
        "criteria": rows,
        "sum_of_contributions": round(total, 6),
        "cci_base": cci_base,
        # The identity is exact; only 6-decimal storage rounding separates the
        # two numbers, so a mismatch above 1e-5 means something is actually wrong.
        "reconciles": abs(total - (cci_base or 0.0)) < 1e-5,
        "top_driver": rows[0]["criterion"] if rows else None,
        "largest_penalty": (max(rows, key=lambda r: r["forgone"] or 0.0)
                            ["criterion"] if rows else None),
        "method": METHOD_EXACT,
        "method_note": ("Each criterion's share is d-_j/(d+ + d-), and d- is a "
                        "plain sum over criteria, so the shares add up to CCi "
                        "exactly. This is arithmetic, not an attribution model."),
    }


def _driver_phrase(attribution: dict, lang: str) -> str:
    """Name the criterion that drove the score, in words, for the citizen text."""
    code = attribution.get("top_driver")
    labels = CRITERION_LABELS.get(code or "", {})
    key = "citizen_mr" if lang == "mr" else "citizen_en"
    fallback = "मूल्यांकन निकष" if lang == "mr" else "the assessment criteria"
    return labels.get(key) or fallback


def citizen_message(*, reason_code: str, ref_no: str | None, rank: Any,
                    total: Any, dispatch_date: str | None,
                    attribution: dict, lang: str = "en",
                    outranked_deferred: int = 0) -> dict:
    """The sentence that actually reaches the person who complained.

    Deliberately says four things and no more: what was decided, where the
    complaint stood among the ones competing with it, which factor drove that
    position, and what happens next. Anything longer does not get read; anything
    shorter is indistinguishable from an automated brush-off.

    ``outranked_deferred`` adds a fifth sentence in the one case that needs it --
    work done ahead of a higher-ranked complaint -- rather than leaving the
    citizen to infer favouritism from a rank they can see is out of order.
    """
    template = CITIZEN_TEMPLATES.get(reason_code) or CITIZEN_TEMPLATES[
        "deferred_capacity_used_by_higher_value_set"]
    lang = "mr" if lang == "mr" else "en"
    body = template[lang].format(
        ref=ref_no or "-",
        date=dispatch_date or ("आज" if lang == "mr" else "today"),
        rank=_ordinal(rank) if lang == "en" else str(rank or "-"),
        total=total or "-",
        driver=_driver_phrase(attribution, lang))
    fit = template.get(f"fit_{lang}") if outranked_deferred > 0 else None
    if fit:
        body = f"{body} {fit}"
    next_step = template[f"next_{lang}"]
    return {
        "language": lang,
        "message": f"{body} {next_step}",
        "outcome_sentence": body,
        "next_step": next_step,
        "translation_status": (TRANSLATION_STATUS if lang == "mr"
                               else "source_language"),
    }

def officer_rationale(*, ticket: dict, score: dict, decision: dict | None,
                      attribution: dict, adjustment: dict,
                      rivals: Sequence[dict]) -> str:
    """The defensible version, with every number a reviewer would ask for.

    Written as prose rather than a table because this is the text that ends up
    quoted in an RTS reply or read out in a ward meeting, where "d+ 0.41 / d- 0.63"
    on its own persuades nobody but "0.63 of the distance was towards the ideal
    profile" does.
    """
    parts: list[str] = []
    base = score.get("cci_base") or 0.0
    value = score.get("cci") or 0.0
    parts.append(
        f"{ticket.get('ref_no') or ticket.get('id')} ({ticket.get('category')}"
        f"{', ' + ticket['ward_id'] if ticket.get('ward_id') else ''}) scored a "
        f"closeness coefficient of {base:.4f} under weight version "
        f"{score.get('weight_version')}, from a distance of "
        f"{score.get('d_negative'):.4f} towards the ideal profile against "
        f"{score.get('d_positive'):.4f} away from it.")

    ranked = attribution.get("criteria") or []
    if ranked:
        driver = ranked[0]
        parts.append(
            f"The largest single contribution was {driver['label']} at "
            f"{driver['contribution']:.4f} ({(driver['share_of_score'] or 0) * 100:.0f}"
            f"% of the score); the four contributions sum to {attribution['sum_of_contributions']:.4f}, "
            f"which is the score itself rather than an approximation of it.")
        penalty = min(ranked, key=lambda r: r["contribution"] or 0.0)
        parts.append(f"The weakest criterion was {penalty['label']}, which "
                     f"cost it {penalty['forgone']:.4f}.")

    uplift = (adjustment.get("community_uplift") or 0.0)
    clock = (adjustment.get("sla_bonus") or 0.0)
    if uplift or clock:
        reasons = []
        if uplift:
            reasons.append(
                f"{adjustment.get('community_multiplier')}x repeat reports added "
                f"{uplift:.4f}")
        if clock:
            reasons.append(f"the deadline state "
                           f"({adjustment.get('sla_reason')}) added {clock:.4f}")
        parts.append(
            "Dispatch value rose from " + f"{base:.4f} to {value:.4f}: "
            + " and ".join(reasons)
            + ". Both act on the remaining gap to 1.0, so neither can overtake a "
              "ticket that already matches the ideal profile.")
    else:
        parts.append(f"No urgency adjustment applied, so the dispatch value "
                     f"equals the raw score ({value:.4f}).")

    if decision:
        parts.append(
            f"Decision: {decision.get('decision')} "
            f"({decision.get('reason_code')}). {decision.get('reason_text')}")
        budget = decision.get("budget_available") or 0.0
        used = decision.get("budget_used") or 0.0
        parts.append(
            f"The run had INR {budget:.0f} and "
            f"{decision.get('workforce_available') or 0:.1f} crew-hours, spent "
            f"INR {used:.0f} and "
            f"{decision.get('workforce_used') or 0:.1f} hours across "
            f"{decision.get('allocated_count')} of "
            f"{decision.get('total_candidates')} candidates, solved by "
            f"{decision.get('solver')}.")
        if decision.get("decision") != "allocated" and rivals:
            named = ", ".join(
                f"{r['ref_no'] or r['ticket_id'][:8]} ({r['category']}, CCi "
                f"{r['cci_score']:.4f}"
                + (f", INR {r['cost_inr']:.0f}" if r["cost_inr"] is not None
                   else ", cost unknown") + ")"
                for r in rivals)
            parts.append(f"The capacity went to: {named}.")
    else:
        parts.append("This ticket was scored but does not appear in a dispatch "
                     "manifest, so no allocation decision has been recorded "
                     "against it yet.")
    return " ".join(parts)

def shap_surrogate(conn, run_id: str, *,
                   ticket_id: str | None = None) -> dict:
    """A SHAP reading of the run, fitted on that run's own cohort.

    Offered because SHAP is the vocabulary reviewers recognise, and refused
    honestly when it cannot be produced:

    * ``scikit-learn``/``shap`` are optional dependencies (``requirements-optional
      .txt``). Their absence returns ``available: false`` with the reason, not a
      500 -- the exact decomposition above is unaffected either way.
    * The council has no historical resolution dataset, so there is nothing to fit
      but the current run. A surrogate fitted on one day's tickets can at best
      reproduce that day's ranking, so its ``r_squared`` is reported: near 1.0 says
      the surrogate mirrors the real function, and anything lower says the SHAP
      numbers are a rough sketch of an exactly known quantity.
    * Fewer than ``min_samples`` scored tickets is refused rather than fitted. A
      forest over four rows produces confident-looking noise.
    """
    min_samples = 8
    rows = query_all(conn, "SELECT ticket_id, cci_base, criteria_snapshot "
                           "FROM ticket_scores WHERE run_id = ?", (run_id,))
    if len(rows) < min_samples:
        return {"available": False, "method": METHOD_SHAP,
                "reason": f"only {len(rows)} scored tickets in this run; a "
                          f"surrogate needs at least {min_samples} to be "
                          f"anything but noise",
                "exact_attribution_unaffected": True}
    try:
        import numpy as np
        import shap
        from sklearn.ensemble import RandomForestRegressor
    except ImportError as exc:
        return {"available": False, "method": METHOD_SHAP,
                "reason": f"optional dependency not installed ({exc.name}); "
                          f"install requirements-optional.txt to enable it",
                "exact_attribution_unaffected": True}

    ids: list[str] = []
    features: list[list[float]] = []
    targets: list[float] = []
    for row in rows:
        snapshot = loads(row["criteria_snapshot"], {}) or {}
        criteria = snapshot.get("criteria") or {}
        if not all(name in criteria for name in CRITERIA):
            continue
        ids.append(row["ticket_id"])
        # The modal value of each TFN is the surrogate's feature. The spread
        # carries the confidence, which a point-estimate forest cannot represent
        # -- another reason this is a second opinion and not the explanation.
        features.append([float(criteria[name][1]) for name in CRITERIA])
        targets.append(float(row["cci_base"] or 0.0))
    if len(features) < min_samples:
        return {"available": False, "method": METHOD_SHAP,
                "reason": "not enough tickets carry a full set of four criteria",
                "exact_attribution_unaffected": True}

    matrix = np.array(features, dtype=float)
    y = np.array(targets, dtype=float)
    model = RandomForestRegressor(n_estimators=200, random_state=42,
                                  min_samples_leaf=1)
    model.fit(matrix, y)
    predicted = model.predict(matrix)
    residual = float(((y - predicted) ** 2).sum())
    spread = float(((y - y.mean()) ** 2).sum())
    r_squared = 1.0 - residual / spread if spread > 1e-12 else 1.0

    values = shap.TreeExplainer(model).shap_values(matrix)
    values = np.array(values, dtype=float)
    if values.ndim == 1:
        values = values.reshape(1, -1)

    per_ticket = {
        tid: {CRITERIA[j]: round(float(values[i][j]), 6)
              for j in range(len(CRITERIA))}
        for i, tid in enumerate(ids)}
    mean_abs = {CRITERIA[j]: round(float(np.abs(values[:, j]).mean()), 6)
                for j in range(len(CRITERIA))}
    result = {
        "available": True,
        "method": METHOD_SHAP,
        "run_id": run_id,
        "cohort_size": len(ids),
        "features": list(CRITERIA),
        "feature_labels": {name: CRITERION_LABELS.get(name, {}).get("en", name)
                           for name in CRITERIA},
        "base_value": round(float(y.mean()), 6),
        "mean_abs_shap": mean_abs,
        "global_ranking": sorted(mean_abs, key=lambda k: -mean_abs[k]),
        "surrogate_r_squared": round(r_squared, 6),
        "fidelity_note": ("The surrogate is fitted on this run's tickets only -- "
                          "no historical resolution dataset exists. Treat these "
                          "values as a familiar-format summary of the exact "
                          "decomposition, which remains authoritative."),
    }
    if ticket_id:
        result["ticket_id"] = ticket_id
        result["shap_values"] = per_ticket.get(ticket_id)
        result["in_cohort"] = ticket_id in per_ticket
    else:
        result["shap_values_by_ticket"] = per_ticket
    return result

def _counterfactual(decision: dict | None, score: dict,
                    ticket: dict) -> dict:
    """What would have to change for the answer to change.

    An explanation that only justifies the past is a defence; one that names the
    lever is a service. Each branch points at a specific, checkable action rather
    than at "priorities may change".
    """
    if decision is None:
        return {"changeable": True,
                "what_would_change_it": "This ticket has not been through a "
                                        "dispatch run yet. Running triage will "
                                        "place it.",
                "owner": "ward officer"}
    reason = decision.get("reason_code")
    if reason in ("allocated", "allocated_mandatory_floor"):
        return {"changeable": False,
                "what_would_change_it": "Already scheduled; nothing needs to "
                                        "change.",
                "owner": None}
    if reason == "deferred_cost_not_estimated":
        return {"changeable": True,
                "what_would_change_it": "Record the repair cost and crew hours "
                                        "on this ticket. It is already ranked "
                                        f"{decision.get('rank_position')} and "
                                        "will be planned at the next run "
                                        "without re-reporting.",
                "owner": "junior engineer / department",
                "endpoint": f"PATCH /api/tickets/{ticket.get('id')}/cost"}
    shortfall_budget = ((decision.get("cost_inr") or 0.0)
                        - ((decision.get("budget_available") or 0.0)
                           - (decision.get("budget_used") or 0.0)))
    shortfall_hours = ((decision.get("hours") or 0.0)
                       - ((decision.get("workforce_available") or 0.0)
                          - (decision.get("workforce_used") or 0.0)))
    if reason == "deferred_exceeds_daily_capacity":
        return {"changeable": True,
                "what_would_change_it": "This needs a multi-day plan or a "
                                        "separate allocation: on its own it "
                                        "exceeds a whole day's budget or crew.",
                "owner": "council / standing committee",
                "budget_shortfall_inr": round(max(shortfall_budget, 0.0), 2),
                "hours_shortfall": round(max(shortfall_hours, 0.0), 2)}
    budget_gap = round(max(shortfall_budget, 0.0), 2)
    hours_gap = round(max(shortfall_hours, 0.0), 2)
    # Name only the dimension that actually ran out. "INR 14900 and 0.0
    # crew-hours" reads like a template that was not thinking, and invites the
    # reader to distrust the figure that *is* real.
    if budget_gap > 0 and hours_gap > 0:
        need = f"about INR {budget_gap:.0f} more and {hours_gap:.1f} more crew-hours"
    elif budget_gap > 0:
        need = f"about INR {budget_gap:.0f} more on the day's budget"
    elif hours_gap > 0:
        need = f"about {hours_gap:.1f} more crew-hours"
    else:
        # Fits the leftover on its own, yet a different combination won the day.
        need = None
    lever = (f"Raising the day's capacity by {need} would have fitted this "
             "alongside the work that was chosen. Otherwise it rises as its "
             "deadline approaches."
             if need else
             "It fits within what was left over, but a different combination of "
             "complaints covered more overall. It carries forward and rises as "
             "its deadline approaches.")
    return {"changeable": True,
            "what_would_change_it": lever,
            "owner": "ward officer (capacity) or time",
            "budget_shortfall_inr": budget_gap,
            "hours_shortfall": hours_gap}

def explain_ticket(conn, ticket_id: str, *, run_id: str | None = None,
                   include_shap: bool = False, persist: bool = True) -> dict:
    """Everything known about why this ticket got the position it got.

    Returns ``None`` only when the ticket does not exist; a ticket that exists but
    has never been scored gets a body explaining *that*, because "we have not
    assessed your complaint yet" is itself an answer the citizen is owed and is
    very different from "we assessed it and it lost".
    """
    ticket = ticket_service.get_ticket(conn, ticket_id)
    if ticket is None:
        return None

    score = _score_row(conn, ticket_id, run_id)
    if score is None:
        return {
            "ticket_id": ticket_id,
            "ref_no": ticket.get("ref_no"),
            "scored": False,
            "status": ticket.get("status"),
            "reason": "no_score_recorded",
            "citizen_message_en": (
                f"Your complaint {ticket.get('ref_no') or ''} has been logged "
                f"and is in the queue, but it has not yet been through a "
                f"prioritisation run, so there is no decision to report. It has "
                f"not been closed or set aside.").strip(),
            "citizen_message_mr": (
                f"तुमची तक्रार {ticket.get('ref_no') or ''} नोंदवली गेली आहे व "
                f"रांगेत आहे, परंतु ती अद्याप प्राधान्यक्रम प्रक्रियेतून गेली "
                f"नाही, म्हणून सांगण्यासारखा निर्णय नाही. ती बंद केलेली नाही.").strip(),
            "translation_status": TRANSLATION_STATUS,
            "sla": ticket.get("sla"),
        }

    snapshot = loads(score["criteria_snapshot"], {}) or {}
    adjustment = snapshot.get("adjustment") or {}
    attribution = shape_attribution(snapshot.get("attribution") or [],
                                    score["cci_base"])
    # ``query_one`` hands back an ``sqlite3.Row``, which indexes but does not
    # ``.get``. Converting once here means the rest of the function can treat a
    # missing decision (a scored ticket that never reached a manifest) and a
    # missing column the same way, instead of guarding every access twice.
    decision = _decision_row(conn, ticket_id, score["run_id"])
    decision = dict(decision) if decision is not None else None
    rivals = (_rivals(conn, decision["manifest_id"], ticket_id)
              if decision and decision.get("decision") != "allocated" else [])
    reason_code = (decision or {}).get("reason_code") or "not_yet_allocated"
    dispatch_date = (decision or {}).get("dispatch_date")
    total = (decision or {}).get("total_candidates")
    rank = score["rank_position"]
    # Only asked when the ticket was actually scheduled; for a deferred ticket
    # the rivals list already carries the same information more concretely.
    outranked = (_better_ranked_deferred(conn, decision["manifest_id"], rank)
                 if decision and decision.get("decision") == "allocated" else 0)

    english = citizen_message(reason_code=reason_code,
                              ref_no=ticket.get("ref_no"), rank=rank,
                              total=total, dispatch_date=dispatch_date,
                              attribution=attribution, lang="en",
                              outranked_deferred=outranked)
    marathi = citizen_message(reason_code=reason_code,
                              ref_no=ticket.get("ref_no"), rank=rank,
                              total=total, dispatch_date=dispatch_date,
                              attribution=attribution, lang="mr",
                              outranked_deferred=outranked)
    rationale = officer_rationale(ticket=ticket, score=dict(score),
                                  decision=decision,
                                  attribution=attribution,
                                  adjustment=adjustment, rivals=rivals)

    body = {
        "ticket_id": ticket_id,
        "ref_no": ticket.get("ref_no"),
        "scored": True,
        "run_id": score["run_id"],
        "weight_version": score["weight_version"],
        "dispatch_date": dispatch_date,
        "manifest_id": (decision or {}).get("manifest_id"),
        "category": ticket.get("category"),
        "ward_id": ticket.get("ward_id"),
        "status": ticket.get("status"),
        "rank": rank,
        "topsis_rank": snapshot.get("topsis_rank"),
        "of_candidates": total,
        "cci_score": score["cci"],
        "cci_base": score["cci_base"],
        "d_positive": score["d_positive"],
        "d_negative": score["d_negative"],
        "criteria_tfns": snapshot.get("criteria") or {},
        "attribution": attribution,
        "urgency_adjustment": adjustment,
        "sla": snapshot.get("sla") or {},
        "decision": (decision or {}).get("decision"),
        "reason_code": (decision or {}).get("reason_code"),
        "reason_text": (decision or {}).get("reason_text"),
        "cost_status": ticket.get("cost_status"),
        "estimated_cost_inr": (decision or {}).get("cost_inr"),
        "estimated_hours": (decision or {}).get("hours"),
        "capacity_context": {
            "budget_available": (decision or {}).get("budget_available"),
            "budget_used": (decision or {}).get("budget_used"),
            "workforce_available": (decision or {}).get("workforce_available"),
            "workforce_used": (decision or {}).get("workforce_used"),
            "allocated_count": (decision or {}).get("allocated_count"),
            "total_candidates": total,
            "solver": (decision or {}).get("solver"),
            "budget_outcome": (decision or {}).get("budget_outcome"),
        },
        "capacity_went_to": rivals,
        "outranked_deferred_count": outranked,
        "what_would_change_it": _counterfactual(decision, dict(score), ticket),
        "citizen_message_en": english["message"],
        "citizen_message_mr": marathi["message"],
        "citizen_messages": {"en": english, "mr": marathi},
        "officer_rationale": rationale,
        "method": METHOD_EXACT,
    }
    if include_shap:
        body["shap"] = shap_surrogate(conn, score["run_id"],
                                      ticket_id=ticket_id)

    if persist:
        _store(conn, body)
    return body

def _store(conn, body: dict) -> str | None:
    """Persist the explanation once per (ticket, run).

    Kept idempotent rather than append-only: re-reading an explanation is a
    harmless GET and must not grow the table, but the *text that was sent to a
    citizen* has to survive, because a later weight change would otherwise leave
    the council unable to reproduce what it told someone. One row per run gives
    both -- stable on re-read, preserved across runs.
    """
    existing = query_one(conn, "SELECT id FROM ticket_explanations WHERE "
                               "ticket_id = ? AND run_id IS ? AND method = ?",
                         (body["ticket_id"], body.get("run_id"), METHOD_EXACT))
    if existing is not None:
        return existing["id"]
    row_id = new_id()
    insert(conn, "ticket_explanations", {
        "id": row_id,
        "ticket_id": body["ticket_id"],
        "run_id": body.get("run_id"),
        "method": METHOD_EXACT,
        "attribution": dumps(body["attribution"]),
        "top_driver": body["attribution"].get("top_driver"),
        "decision": body.get("decision"),
        "citizen_message_en": body.get("citizen_message_en"),
        "citizen_message_mr": body.get("citizen_message_mr"),
        "officer_rationale": body.get("officer_rationale"),
        "created_at": utcnow_iso(),
    })
    # The citizen-facing sentence is the artefact an RTS appeal actually tests,
    # so what was said and when is audited. try_append: an explanation that
    # cannot be audited is still better delivered than withheld, and the row
    # above is already idempotent per (ticket, run).
    audit.try_append(conn, audit.ACTION_EXPLANATION_STORED,
                     entity_type=audit.ENTITY_EXPLANATION, entity_id=row_id,
                     payload={
                         "ticket_id": body["ticket_id"],
                         "ref_no": body.get("ref_no"),
                         "run_id": body.get("run_id"),
                         "method": METHOD_EXACT,
                         "decision": body.get("decision"),
                         "top_driver": body["attribution"].get("top_driver"),
                         "citizen_message_en": body.get("citizen_message_en"),
                         "citizen_message_mr": body.get("citizen_message_mr"),
                         "translation_status": TRANSLATION_STATUS,
                     })
    return row_id


def explanation_history(conn, ticket_id: str) -> list[dict]:
    """Every explanation ever stored for a ticket, oldest first.

    This is the evidence that the platform said the same thing to the citizen
    that it recorded internally, on each occasion -- which is the part an RTS
    appeal or an audit actually tests.
    """
    rows = query_all(conn, "SELECT * FROM ticket_explanations WHERE "
                           "ticket_id = ? ORDER BY created_at, rowid",
                     (ticket_id,))
    out: list[dict] = []
    for row in rows:
        entry = dict(row)
        entry["attribution"] = loads(entry.get("attribution"), {})
        out.append(entry)
    return out


def latest_run_id(conn) -> str | None:
    """The most recent scoring run, so callers can say 'latest' and mean it.

    Resolved from ``ticket_scores`` rather than from the manifest table because a
    dry run scores tickets without ever writing a manifest, and an officer
    reviewing "what did the last run decide" means that one too.
    """
    row = query_one(conn, "SELECT run_id FROM ticket_scores "
                          "ORDER BY created_at DESC, rowid DESC LIMIT 1")
    return row["run_id"] if row else None


def explain_run(conn, run_id: str, *, limit: int = 100) -> dict:
    """One line per ticket in a run: score, decision, driver, citizen sentence.

    Built for the review screen an officer opens after a run, where the question
    is not "why this ticket" but "does the whole day's plan look defensible".
    """
    rows = query_all(conn, "SELECT ticket_id FROM ticket_scores WHERE run_id = ? "
                           "ORDER BY rank_position LIMIT ?",
                     (run_id, int(limit)))
    explanations = []
    for row in rows:
        body = explain_ticket(conn, row["ticket_id"], run_id=run_id,
                              persist=True)
        if body is None:
            continue
        explanations.append({
            "ticket_id": body["ticket_id"],
            "ref_no": body.get("ref_no"),
            "rank": body.get("rank"),
            "category": body.get("category"),
            "ward_id": body.get("ward_id"),
            "cci_score": body.get("cci_score"),
            "cci_base": body.get("cci_base"),
            "decision": body.get("decision"),
            "reason_code": body.get("reason_code"),
            "top_driver": body["attribution"].get("top_driver"),
            "citizen_message_en": body.get("citizen_message_en"),
            "citizen_message_mr": body.get("citizen_message_mr"),
        })
    return {"run_id": run_id, "count": len(explanations),
            "explanations": explanations,
            "method": METHOD_EXACT,
            "translation_status": TRANSLATION_STATUS}

if __name__ == "__main__":  # pragma: no cover
    # Redirected before the first-party imports below would otherwise bind the
    # real database path -- same reason as in services/prioritisation.py.
    import os
    import shutil
    import tempfile

    _SCRATCH = Path(tempfile.gettempdir()) / "crpp_explain_selftest"
    shutil.rmtree(_SCRATCH, ignore_errors=True)
    (_SCRATCH / "uploads").mkdir(parents=True, exist_ok=True)
    os.environ["CRPP_DB_PATH"] = str(_SCRATCH / "selftest.db")
    os.environ["UPLOAD_DIR"] = str(_SCRATCH / "uploads")

if __name__ == "__main__":  # pragma: no cover
    from database import get_conn, init_db
    from services import prioritisation as triage

    init_db()

    # --- citizen text, checked without a database -----------------------------
    fake_attr = shape_attribution([
        {"criterion": "C2_safety", "contribution": 0.31, "forgone": 0.05,
         "share_of_score": 0.50},
        {"criterion": "C1_infra", "contribution": 0.20, "forgone": 0.09,
         "share_of_score": 0.32},
        {"criterion": "C3_equity", "contribution": 0.08, "forgone": 0.12,
         "share_of_score": 0.13},
        {"criterion": "C4_cost", "contribution": 0.03, "forgone": 0.20,
         "share_of_score": 0.05},
    ], 0.62)
    assert fake_attr["top_driver"] == "C2_safety", fake_attr
    assert fake_attr["reconciles"], fake_attr
    assert fake_attr["largest_penalty"] == "C4_cost", fake_attr

    print("every reason code produces a citizen sentence in both languages:")
    for code in CITIZEN_TEMPLATES:
        for lang in ("en", "mr"):
            msg = citizen_message(reason_code=code, ref_no="KMC-20260829-0007",
                                  rank=3, total=11, dispatch_date="2026-08-29",
                                  attribution=fake_attr, lang=lang)
            assert "{" not in msg["message"], (code, lang, msg)
            assert len(msg["message"]) > 40, (code, lang)
            assert msg["next_step"] and msg["next_step"] in msg["message"]
        print(f"   {code:<45} en+mr  OK")
    # An unknown reason code must still say something rather than raise: a
    # citizen-facing path may not fail because a new code was added upstream.
    fallback = citizen_message(reason_code="a_code_added_later", ref_no="X",
                               rank=1, total=2, dispatch_date="2026-08-29",
                               attribution=fake_attr)
    assert "{" not in fallback["message"] and fallback["message"]
    print("   unknown reason code falls back safely                OK\n")

    with get_conn() as conn:
        cases = [
            ("live electrical wire down across the lane", "road_damage",
             "Ward-4", 19.8811, 74.4785, {"sensitive_site": "hospital",
                                          "affected_population": 2400}),
            ("drain blocked, sewage on the street", "drain_blockage", "Ward-4",
             19.8830, 74.4800, {"affected_population": 900}),
            ("pothole on the approach road", "road_damage", "Ward-9",
             19.8600, 74.4700, {"affected_population": 200}),
            ("street light out near the school", "streetlight_failure",
             "Ward-9", 19.8620, 74.4720, {"sensitive_site": "school",
                                          "affected_population": 400}),
            ("water not coming since morning", "water_distribution_failure",
             "Ward-2", 19.8700, 74.4600, {"affected_population": 1500}),
        ]
        made = []
        for i, (desc, category, ward, lat, lon, extra) in enumerate(cases):
            made.append(ticket_service.create_ticket(
                conn, {"citizen_phone": f"90000000{i:02d}", "category": category,
                       "description": desc, "ward_id": ward, "lat": lat,
                       "lon": lon, **extra}, [], actor="selftest"))

        # A ticket that has never been through a run must still get an answer.
        unscored = explain_ticket(conn, made[0]["ticket_id"])
        assert unscored["scored"] is False, unscored
        assert unscored["reason"] == "no_score_recorded"
        assert unscored["citizen_message_en"] and unscored["citizen_message_mr"]
        print("unscored ticket still gets an answer:")
        print(f"   en: {unscored['citizen_message_en']}")
        print(f"   mr: {unscored['citizen_message_mr']}\n")
        assert explain_ticket(conn, "no-such-ticket") is None

        for entry, cost, hours in zip(made, (18_000, 9_000, 4_500, None, None),
                                      (9.0, 5.0, 3.0, None, None)):
            if cost is None:
                continue
            ticket_service.update_cost_inputs(
                conn, entry["ticket_id"],
                {"runtime_material_cost": cost * 0.55,
                 "runtime_labour_cost": cost * 0.30,
                 "runtime_vehicle_cost": cost * 0.15,
                 "crew_hours": hours}, actor="selftest")

        triage.set_capacity(conn, budget_inr=25_000, workforce_hours=18,
                            verified_by="ward_engineer_selftest")
        run = triage.run_triage(conn, actor="selftest")
        print(run["message"] + "\n")

        rows = sorted(run["allocated"] + run["deferred"],
                      key=lambda r: r["rank"])
        for row in rows:
            body = explain_ticket(conn, row["ticket_id"], include_shap=False)
            assert body["scored"] is True
            assert body["attribution"]["reconciles"], body["ref_no"]
            assert body["attribution"]["top_driver"] in CRITERIA
            assert body["decision"] == row["decision"]
            assert body["reason_code"] == row["reason_code"]
            assert "{" not in body["citizen_message_en"]
            assert "{" not in body["citizen_message_mr"]
            assert body["officer_rationale"].startswith(str(body["ref_no"]))
            # A deferred ticket must be told what took the capacity, and be given
            # a lever. "Deferred" with no next step is how a queue loses trust.
            lever = body["what_would_change_it"]
            if body["decision"] == "allocated":
                assert lever["changeable"] is False, body["ref_no"]
            else:
                assert lever["changeable"] is True and lever["owner"], lever
                if body["reason_code"] == "deferred_capacity_used_by_higher_value_set":
                    assert body["capacity_went_to"], body["ref_no"]

            print(f"rank {body['rank']}  {body['ref_no']}  "
                  f"{body['decision']}  ({body['reason_code']})")
            print(f"   driver: {body['attribution']['top_driver']}  "
                  f"CCi {body['cci_score']:.4f} = "
                  + " + ".join(f"{c['criterion']} {c['contribution']:.3f}"
                               for c in body["attribution"]["criteria"]))
            print(f"   en: {body['citizen_message_en']}")
            print(f"   mr: {body['citizen_message_mr']}")
            print(f"   lever: {lever['what_would_change_it']}")
            print()

        # --- persistence ------------------------------------------------------
        first = explain_ticket(conn, rows[0]["ticket_id"])
        again = explain_ticket(conn, rows[0]["ticket_id"])
        history = explanation_history(conn, rows[0]["ticket_id"])
        assert len(history) == 1, f"re-reading created {len(history)} rows"
        assert history[0]["citizen_message_en"] == first["citizen_message_en"]
        assert history[0]["citizen_message_mr"]
        assert again["citizen_message_en"] == first["citizen_message_en"]
        print("re-reading an explanation is idempotent (1 stored row)  OK")

        # A second run must add a second stored explanation, not overwrite the
        # first: the council has to be able to show what it said, and when.
        triage.run_triage(conn, budget=120_000, workforce=90, actor="selftest")
        explain_ticket(conn, rows[0]["ticket_id"])
        history = explanation_history(conn, rows[0]["ticket_id"])
        assert len(history) == 2, [h["run_id"] for h in history]
        assert history[0]["run_id"] != history[1]["run_id"]
        print("a second run stores a second explanation, first preserved  OK")

        # --- run-level review -------------------------------------------------
        review = explain_run(conn, run["run_id"])
        assert review["count"] == len(rows), review["count"]
        assert all(e["citizen_message_en"] for e in review["explanations"])
        print(f"run review returns {review['count']} lines, every one with a "
              f"citizen sentence  OK")

        # --- SHAP: optional, and honest about it -------------------------------
        shap_out = shap_surrogate(conn, run["run_id"],
                                  ticket_id=rows[0]["ticket_id"])
        if shap_out["available"]:
            assert shap_out["surrogate_r_squared"] <= 1.0 + 1e-9
            print(f"SHAP surrogate available: R^2 "
                  f"{shap_out['surrogate_r_squared']:.4f}, global order "
                  f"{shap_out['global_ranking']}")
        else:
            print(f"SHAP surrogate unavailable, refused cleanly: "
                  f"{shap_out['reason']}")
        assert shap_out["exact_attribution_unaffected"] is True or \
            shap_out["available"]

        print("\nself-test passed.")

