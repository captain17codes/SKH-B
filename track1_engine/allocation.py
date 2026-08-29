"""Multi-constraint 0/1 knapsack: which complaints get today's crew and money.

The prioritisation step produces an order. This step produces a *plan*, and the
two are not the same thing: the highest-ranked ticket may cost more than the
whole day's budget, and taking it would strand three near-equal tickets that
together do far more good. Greedy dispatch by rank is the fixed rule the brief
warns against; this is the optimisation that replaces it.

Formally: maximise sum of ticket value subject to two simultaneous capacities
(rupees and crew-hours). That is the 2-dimensional 0/1 knapsack, which is
NP-hard in general and trivial at Kopargaon's daily scale (tens of open tickets,
not thousands).

What this implementation does that the naive version did not:

* **Prunes dominated states.** The old sparse DP kept every reachable
  (budget, hours) pair, so state count grew multiplicatively and a day with 40
  tickets could stall. A state is dominated when another state spends no more
  money, no more hours, and achieves at least as much value; dominated states can
  never lead to a better plan, so they are discarded. This is exact -- it removes
  no optimal solution.
* **Never claims optimality it did not achieve.** If the frontier still exceeds
  ``max_states`` after pruning it is truncated to the most valuable states and
  the result is labelled ``dp_beam`` instead of ``optimal``. A manifest that says
  "near-optimal, 5000-state beam" is defensible; one that says "OPTIMAL" when it
  was a heuristic is not.
* **Honours mandatory items.** A ticket whose statutory or safety floor is
  critical is not an optimisation candidate at all -- life-safety cannot be
  traded against three cheap potholes. Mandatory tickets are committed first and
  the knapsack optimises whatever capacity remains. If they alone exceed
  capacity, the run says so (``budget_outcome = "mandatory_over_capacity"``)
  rather than quietly dropping one.
* **Reports the reason each ticket lost.** Deferral without a reason is what
  makes citizens distrust a queue, so every unselected ticket gets a machine
  reason code: it did not fit, its cost is unknown, or it fit but a better
  combination used the capacity.

``knapsack_allocate`` keeps its original signature and ``(ids, score)`` return so
existing tests and callers are unaffected; ``allocate`` is the richer entry point
the API uses.
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Sequence

# Rupees and hours are rounded to this many decimals when used as a state key.
# Two plans that differ by a hundredth of a rupee are the same plan; without this
# float noise would create distinct states that pruning cannot collapse.
STATE_PRECISION = 2

# Safety valve. Reached only on days far larger than Kopargaon produces.
DEFAULT_MAX_STATES = 20_000


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


State = tuple[float, float, float, tuple]

NEG_INF = float("-inf")


def _prune(states: list[State]) -> list[State]:
    """Drop states another state beats on every axis at once.

    A state is (budget_used, hours_used, value, items). State A dominates B when
    A spends no more of either resource and earns at least as much value; B can
    then never be part of a strictly better plan, so it is removed. Removing them
    is exact: any completion open to B is open to A for at least as much value.

    The obvious implementation compares every state against every survivor, which
    is quadratic and measurably too slow -- 60 tickets took 23 seconds, inside a
    request that has to answer a ward officer. Instead this sweeps the states in
    increasing budget order, so every state already seen spends no more money than
    the current one, and asks a single question of the ones seen so far: *among
    those using no more crew-hours, was any worth at least as much?* If yes the
    current state is dominated. That question is a prefix maximum over the
    hours axis, which a Fenwick tree answers in log time, taking the whole pass to
    O(n log n).

    Ordering detail that makes the sweep sound: ties sort hours ascending and
    value descending, so a state is only ever compared against states that could
    genuinely dominate it, never against one that merely looks equal.
    """
    if len(states) <= 1:
        return list(states)

    # Compress the hours values seen in this call into 1..size Fenwick indices.
    hour_levels = sorted({state[1] for state in states})
    index_of = {hours: i + 1 for i, hours in enumerate(hour_levels)}
    size = len(hour_levels)
    tree = [NEG_INF] * (size + 1)

    def record(i: int, value: float) -> None:
        while i <= size:
            if tree[i] < value:
                tree[i] = value
            i += i & -i

    def best_upto(i: int) -> float:
        best = NEG_INF
        while i > 0:
            if tree[i] > best:
                best = tree[i]
            i -= i & -i
        return best

    states.sort(key=lambda s: (s[0], s[1], -s[2]))
    frontier: list[State] = []
    for state in states:
        slot = index_of[state[1]]
        if best_upto(slot) >= state[2]:
            continue  # some cheaper-or-equal state already earns at least this
        frontier.append(state)
        record(slot, state[2])

    # solve_dp truncates the frontier to the most valuable states when it grows
    # past the beam limit, so hand it back value-descending.
    frontier.sort(key=lambda s: (-s[2], s[0], s[1]))
    return frontier


def solve_dp(candidates: Sequence[dict], budget: float, workforce: float,
             *, value_key: str = "value",
             max_states: int = DEFAULT_MAX_STATES) -> dict:
    """Exact 2-D knapsack by reachable-state DP with dominance pruning."""
    # (budget_used, hours_used, value, items)
    states: list[State] = [(0.0, 0.0, 0.0, ())]
    truncated = False

    for item in candidates:
        cost = _num(item.get("budget_cost"))
        hours = _num(item.get("workforce_hours"))
        value = _num(item.get(value_key, item.get("topsis_score")))
        item_id = item["id"]

        grown: list[State] = []
        for used_budget, used_hours, acc_value, items in states:
            new_budget = round(used_budget + cost, STATE_PRECISION)
            new_hours = round(used_hours + hours, STATE_PRECISION)
            if new_budget <= budget and new_hours <= workforce:
                grown.append((new_budget, new_hours, acc_value + value,
                              items + (item_id,)))
        if not grown:
            continue
        states = _prune(states + grown)
        if len(states) > max_states:
            # Already sorted by value descending inside _prune.
            states = states[:max_states]
            truncated = True

    best = max(states, key=lambda s: s[2])
    return {
        "selected": list(best[3]),
        "objective_value": best[2],
        "budget_used": best[0],
        "workforce_used": best[1],
        "solver": "dp_beam" if truncated else "dp_exact",
        "optimal": not truncated,
        "states_explored": len(states),
    }


def solve_cpsat(candidates: Sequence[dict], budget: float, workforce: float,
                *, value_key: str = "value") -> dict | None:
    """Same problem via OR-Tools CP-SAT. Returns None when OR-Tools is absent.

    Kept optional on purpose: the DP above is exact at council scale, so OR-Tools
    is an accelerator for a bigger deployment rather than a dependency the demo
    rests on. CP-SAT is integer-only, so rupees, hours and values are scaled to
    integers -- rupees to the paisa, hours to the minute, value to 1e-6.
    """
    try:
        from ortools.sat.python import cp_model  # type: ignore
    except ImportError:
        return None

    model = cp_model.CpModel()
    picks = [model.NewBoolVar(f"x{i}") for i in range(len(candidates))]

    def scaled(value: float, factor: int) -> int:
        return int(round(_num(value) * factor))

    model.Add(sum(picks[i] * scaled(c.get("budget_cost"), 100)
                  for i, c in enumerate(candidates)) <= scaled(budget, 100))
    model.Add(sum(picks[i] * scaled(c.get("workforce_hours"), 60)
                  for i, c in enumerate(candidates)) <= scaled(workforce, 60))
    model.Maximize(sum(
        picks[i] * scaled(c.get(value_key, c.get("topsis_score")), 1_000_000)
        for i, c in enumerate(candidates)))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    chosen = [c for i, c in enumerate(candidates) if solver.Value(picks[i])]
    return {
        "selected": [c["id"] for c in chosen],
        "objective_value": sum(_num(c.get(value_key, c.get("topsis_score")))
                               for c in chosen),
        "budget_used": round(sum(_num(c.get("budget_cost")) for c in chosen),
                             STATE_PRECISION),
        "workforce_used": round(sum(_num(c.get("workforce_hours"))
                                    for c in chosen), STATE_PRECISION),
        "solver": "ortools_cpsat",
        "optimal": status == cp_model.OPTIMAL,
        "states_explored": None,
    }


# Machine-readable deferral reasons. A citizen-facing sentence is generated from
# these later; keeping the code separate from the prose means the explanation and
# the decision can never drift apart.
REASON_ALLOCATED = "allocated"
REASON_MANDATORY = "allocated_mandatory_floor"
REASON_COST_UNKNOWN = "deferred_cost_not_estimated"
REASON_EXCEEDS_CAPACITY = "deferred_exceeds_daily_capacity"
REASON_OUTBID = "deferred_capacity_used_by_higher_value_set"

REASON_TEXT = {
    REASON_ALLOCATED: "Selected within today's budget and crew hours.",
    REASON_MANDATORY: "Committed before optimisation: a safety or statutory "
                      "floor makes this non-negotiable.",
    REASON_COST_UNKNOWN: "No cost estimate yet, so it cannot be planned against "
                         "a budget. It keeps its rank and is scheduled as soon "
                         "as a cost is entered.",
    REASON_EXCEEDS_CAPACITY: "On its own it needs more than one day's budget or "
                             "crew hours; it needs a multi-day plan or a "
                             "capacity increase, not a queue position.",
    REASON_OUTBID: "It fits, but the same capacity served a combination of "
                   "higher-priority work. It carries forward and its rank "
                   "improves as its deadline approaches.",
}


def allocate(tickets: Sequence[dict], daily_budget: float,
             daily_workforce: float, *, value_key: str = "value",
             solver: str | None = None,
             max_states: int = DEFAULT_MAX_STATES) -> dict:
    """Plan one day's work. Returns the decision for *every* ticket, with reasons.

    ``tickets`` need ``id``, ``budget_cost``, ``workforce_hours`` and a value
    (``value_key``, falling back to ``topsis_score``). Two optional flags change
    the treatment: ``mandatory`` forces selection ahead of the optimisation, and
    ``cost_known=False`` withdraws a ticket from the optimisation entirely
    because planning it against a budget would mean inventing a number.

    ``solver`` is ``auto`` (default), ``ortools`` or ``dp``; ``auto`` prefers
    CP-SAT when installed and falls back to the exact DP.
    """
    solver = (solver or os.getenv("KNAPSACK_SOLVER") or "auto").lower()
    budget = _num(daily_budget)
    workforce = _num(daily_workforce)

    mandatory = [t for t in tickets if t.get("mandatory")]
    unknown_cost = [t for t in tickets
                    if not t.get("mandatory") and t.get("cost_known") is False]
    optional = [t for t in tickets
                if not t.get("mandatory") and t.get("cost_known") is not False]

    committed_budget = sum(_num(t.get("budget_cost")) for t in mandatory)
    committed_hours = sum(_num(t.get("workforce_hours")) for t in mandatory)
    over_capacity = (committed_budget > budget or committed_hours > workforce)

    remaining_budget = max(0.0, budget - committed_budget)
    remaining_hours = max(0.0, workforce - committed_hours)

    # A ticket that cannot fit even in an empty day is not an optimisation
    # candidate; separating it out shrinks the DP and yields a truer reason.
    feasible, infeasible = [], []
    for item in optional:
        if (_num(item.get("budget_cost")) > remaining_budget
                or _num(item.get("workforce_hours")) > remaining_hours):
            infeasible.append(item)
        else:
            feasible.append(item)

    result = None
    if solver in ("auto", "ortools"):
        result = solve_cpsat(feasible, remaining_budget, remaining_hours,
                             value_key=value_key)
    if result is None:
        result = solve_dp(feasible, remaining_budget, remaining_hours,
                          value_key=value_key, max_states=max_states)

    chosen = set(result["selected"])
    # Membership is tested by object identity, not by ``==``. Two tickets can hold
    # equal dicts (same category, same cost, both cost-unknown) and value equality
    # would then tag the wrong one; identity cannot be confused that way.
    unknown_ids = {id(t) for t in unknown_cost}
    infeasible_ids = {id(t) for t in infeasible}

    decisions: list[dict] = []
    for item in tickets:
        item_id = item["id"]
        if item.get("mandatory"):
            code = REASON_MANDATORY
        elif id(item) in unknown_ids:
            code = REASON_COST_UNKNOWN
        elif item_id in chosen:
            code = REASON_ALLOCATED
        elif id(item) in infeasible_ids:
            code = REASON_EXCEEDS_CAPACITY
        else:
            code = REASON_OUTBID
        decisions.append({
            "id": item_id,
            "decision": "allocated" if code in (REASON_ALLOCATED,
                                                REASON_MANDATORY)
                        else "deferred",
            "reason_code": code,
            "reason_text": REASON_TEXT[code],
            "value": _num(item.get(value_key, item.get("topsis_score"))),
            "budget_cost": _num(item.get("budget_cost")),
            "workforce_hours": _num(item.get("workforce_hours")),
        })

    allocated_ids = [d["id"] for d in decisions if d["decision"] == "allocated"]
    return {
        "selected": allocated_ids,
        "decisions": decisions,
        "objective_value": round(
            result["objective_value"]
            + sum(_num(t.get(value_key, t.get("topsis_score")))
                  for t in mandatory), 6),
        "budget_available": budget,
        "workforce_available": workforce,
        "budget_used": round(result["budget_used"] + committed_budget,
                             STATE_PRECISION),
        "workforce_used": round(result["workforce_used"] + committed_hours,
                                STATE_PRECISION),
        "mandatory_count": len(mandatory),
        "cost_unknown_count": len(unknown_cost),
        "infeasible_count": len(infeasible),
        "allocated_count": len(allocated_ids),
        "deferred_count": len(decisions) - len(allocated_ids),
        "solver": result["solver"],
        "optimal": bool(result["optimal"]) and not over_capacity,
        "states_explored": result.get("states_explored"),
        "budget_outcome": ("mandatory_over_capacity" if over_capacity else
                           "within_capacity"),
        "notes": ([f"mandatory tickets alone need INR {committed_budget:.0f} and "
                   f"{committed_hours:.1f} crew-hours, which exceeds today's "
                   f"capacity; they are still committed because a safety or "
                   f"statutory floor applies. Escalate for extra capacity."]
                  if over_capacity else []),
    }


def knapsack_allocate(tickets, daily_budget, daily_workforce):
    """Original entry point: ``(allocated_ticket_ids, total_value)``.

    Retained unchanged so ``tests/test_engine.py`` and any existing caller keep
    working. New code should call :func:`allocate`, which returns the reason each
    ticket was or was not selected -- the part a citizen is owed.
    """
    plan = allocate(tickets, daily_budget, daily_workforce,
                    value_key="topsis_score")
    return plan["selected"], plan["objective_value"]


if __name__ == "__main__":  # pragma: no cover
    def show(title: str, plan: dict) -> None:
        print(f"\n{title}")
        print(f"   solver {plan['solver']}  optimal={plan['optimal']}  "
              f"outcome={plan['budget_outcome']}")
        print(f"   spent INR {plan['budget_used']:.0f}/"
              f"{plan['budget_available']:.0f}, "
              f"{plan['workforce_used']:.1f}/"
              f"{plan['workforce_available']:.1f} crew-hours, "
              f"value {plan['objective_value']:.4f}")
        for d in plan["decisions"]:
            print(f"   {d['id']:<10} {d['decision']:<9} {d['reason_code']}")
        for note in plan["notes"]:
            print(f"   note: {note}")

    base = [
        {"id": "t1", "budget_cost": 500, "workforce_hours": 10, "topsis_score": 0.9},
        {"id": "t2", "budget_cost": 200, "workforce_hours": 5, "topsis_score": 0.5},
        {"id": "t3", "budget_cost": 300, "workforce_hours": 4, "topsis_score": 0.6},
        {"id": "t4", "budget_cost": 800, "workforce_hours": 12, "topsis_score": 0.95},
    ]
    show("1. plain 2-D knapsack, budget 700 / 15h "
         "(rank order would take t4 first and strand everything)",
         allocate(base, 700, 15, value_key="topsis_score"))

    ids, value = knapsack_allocate(base, 700, 15)
    assert set(ids) == {"t1", "t2"}, ids
    assert abs(value - 1.4) < 1e-9, value
    print("\n   legacy knapsack_allocate ->", sorted(ids), round(value, 6),
          "(matches tests/test_engine.py)")

    # A live electrical hazard cannot lose to three cheap potholes, so it is
    # committed before the optimisation rather than entered into it.
    with_mandatory = [dict(t) for t in base]
    with_mandatory[3]["mandatory"] = True
    show("2. t4 is a life-safety floor: committed first, and it alone "
         "exceeds today's money", allocate(with_mandatory, 700, 15,
                                          value_key="topsis_score"))

    # An un-costed ticket must not be planned against a budget by inventing a
    # number; it keeps its rank and waits for an estimate.
    with_unknown = [dict(t) for t in base]
    with_unknown[0]["cost_known"] = False
    with_unknown[0]["budget_cost"] = None
    show("3. t1 has no cost estimate yet",
         allocate(with_unknown, 700, 15, value_key="topsis_score"))

    show("4. capacity of zero: every ticket must still get a reason",
         allocate(base, 0, 0, value_key="topsis_score"))

    empty = allocate([], 700, 15, value_key="topsis_score")
    assert empty["selected"] == [] and empty["decisions"] == []
    print(f"\n5. empty day -> {empty['budget_outcome']}, "
          f"solver {empty['solver']}, no decisions")

    # Scale check: dominance pruning is what keeps this from exploding.
    import random
    import time
    random.seed(7)
    big = [{"id": f"k{i}",
            "budget_cost": random.randrange(50, 900),
            "workforce_hours": random.randrange(1, 14),
            "topsis_score": round(random.random(), 4)} for i in range(60)]
    started = time.perf_counter()
    heavy = allocate(big, 12_000, 160, value_key="topsis_score")
    elapsed = time.perf_counter() - started
    print(f"\n6. 60 tickets, INR 12000 / 160h -> "
          f"{heavy['allocated_count']} allocated, value "
          f"{heavy['objective_value']:.4f}, {heavy['states_explored']} states "
          f"on the frontier, {elapsed * 1000:.0f} ms, optimal="
          f"{heavy['optimal']}")

    # Pruning must not change the answer, only the work done to reach it.
    small = big[:14]
    exact = allocate(small, 3_000, 40, value_key="topsis_score")
    brute = 0.0
    for mask in range(1 << len(small)):
        cost = hours = value = 0.0
        for i, t in enumerate(small):
            if mask >> i & 1:
                cost += t["budget_cost"]
                hours += t["workforce_hours"]
                value += t["topsis_score"]
        if cost <= 3_000 and hours <= 40:
            brute = max(brute, value)
    assert abs(exact["objective_value"] - brute) < 1e-9, (
        exact["objective_value"], brute)
    print(f"7. pruned DP vs brute force over 2^14 subsets: "
          f"{exact['objective_value']:.4f} == {brute:.4f}  OK")
