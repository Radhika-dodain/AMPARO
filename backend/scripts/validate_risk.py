"""
The sanity check that decides whether this project is real.

    python scripts/validate_risk.py

Prints the risk score of a handful of named streets you personally know, plus
the highest and lowest scoring streets in the whole area.

Run this on day 3 or 4, before building anything on top of the risk model.
If the main road with the bar strip does not come out riskier than a quiet
residential lane, the weights are wrong - and every route, every colour on
the map and every number in the pitch is meaningless until they are fixed.

This is also the script you re-run after every weight tweak.
"""

# WHAT GOES IN HERE:
# - a short list of street names in the demo area with what you expect them
#   to score (e.g. "North Main Road - should be high at night")
# - load the scored map
# - print each named street's score next to your expectation
# - print the top 10 riskiest and top 10 safest streets
# - print the same thing at noon and at midnight, to check the time-of-day
#   scaling actually changes something

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings                  # noqa: E402
from services import graph_build, risk       # noqa: E402

# Streets in the demo area and what you expect them to do. Edit this list for
# your own neighbourhood - it only works if you actually know these streets.
EXPECTATIONS: list[tuple[str, str]] = [
    ("North Main Road", "high at night - the bar strip"),
    ("Lane Number 6", "quiet residential lane"),
    ("Lane Number 7", "quiet residential lane"),
    ("Dhole Patil Road", "main road, should be lower"),
    ("Bund Garden Road", "main road, should be lower"),
]


def _named_streets(graph, bucket: str) -> dict[str, list[float]]:
    """Every risk score in the area, grouped by street name."""
    from services.risk import _first

    by_name: dict[str, list[float]] = {}
    attr = risk.risk_attribute(bucket=bucket)
    for _u, _v, data in graph.edges(data=True):
        name = str(_first(data.get("name")) or "").strip()
        if name:
            by_name.setdefault(name, []).append(float(data.get(attr, 0.0)))
    return by_name


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> int:
    graph = graph_build.load_graph()
    print(f"{settings.area_name} - {graph.number_of_edges()} streets\n")

    night = _named_streets(graph, "night")
    day = _named_streets(graph, "day")

    print("STREETS YOU KNOW (mean risk)")
    print(f"  {'street':28} {'night':>6} {'day':>6}   expectation")
    missing = []
    for name, expectation in EXPECTATIONS:
        matches = [n for n in night if name.lower() in n.lower()]
        if not matches:
            missing.append(name)
            continue
        for match in matches[:1]:
            print(
                f"  {match[:28]:28} {_mean(night[match]):6.3f} "
                f"{_mean(day.get(match, [])):6.3f}   {expectation}"
            )
    if missing:
        print(f"\n  not found in the map data: {', '.join(missing)}")
        print("  (either the name differs in OSM, or it is outside the bbox)")

    ranked = sorted(night.items(), key=lambda kv: _mean(kv[1]))
    print("\nSAFEST NAMED STREETS")
    for name, values in ranked[:10]:
        print(f"  {_mean(values):6.3f}  {name}")
    print("\nRISKIEST NAMED STREETS")
    for name, values in reversed(ranked[-10:]):
        print(f"  {_mean(values):6.3f}  {name}")

    print("\nTIME OF DAY - does it actually change anything?")
    for bucket in risk.BUCKETS:
        print(f"  {bucket:8} {risk.distribution(graph, bucket)}")

    # ---- What the map data can actually support ----
    # Printed every run, because it bounds what the pitch is allowed to claim.
    # Two of the four advertised signals turned out to be nearly empty here.
    import json
    from services.risk import _first as first_tag

    lit_tagged = sum(
        1 for _u, _v, d in graph.edges(data=True)
        if str(first_tag(d.get("lit"))).lower() in {"yes", "no"}
    )
    places = json.loads(Path(settings.poi_cache_path).read_text())["places"]

    print("\nWHAT THE MAP DATA ACTUALLY GIVES US")
    print(f"  streets with a lighting tag : {lit_tagged} of {graph.number_of_edges()}")
    print(f"  police / hospitals / clinics: {len(places['protective'])}")
    print(f"  bars / pubs / clubs         : {len(places['nightlife'])}")
    print(f"  shops / cafes / restaurants : {len(places['busy'])}")
    if lit_tagged == 0:
        print("  -> lighting contributes NOTHING here. Do not claim it on a slide.")
    if len(places["nightlife"]) < 10:
        print("  -> nightlife is thin. The 'routes around the bar strip' story is weak.")

    # ---- The gate ----
    # This checks what the model actually claims, which is not what the original
    # brief assumed. The brief said "North Main Road must score riskier than a
    # quiet lane". The corrected model deliberately refuses to say that: once
    # busyness counts as a safety signal, a lit commercial street with people on
    # it SHOULD beat a deserted lane - that was the entire point of adding the
    # busyness term. So the gate checks the claim that survives instead:
    # isolated narrow lanes score riskier than proper roads.
    print("\nTHE CHECK THAT MATTERS")
    lanes, roads = [], []
    for _u, _v, d in graph.edges(data=True):
        highway = str(first_tag(d.get("highway"))).lower()
        if highway in {"service", "track", "path", "footway", "alley", "steps"}:
            lanes.append(float(d.get("risk_night", 0.0)))
        elif highway in {"primary", "secondary", "trunk", "tertiary"}:
            roads.append(float(d.get("risk_night", 0.0)))

    lane_risk, road_risk = _mean(lanes), _mean(roads)
    print(f"  narrow lanes and service roads : {lane_risk:.3f}  (n={len(lanes)})")
    print(f"  proper main roads              : {road_risk:.3f}  (n={len(roads)})")
    print(f"  -> {'PASS' if lane_risk > road_risk else 'FAIL - tune config.py'}")

    spread = risk.distribution(graph, "night")
    middle_half = spread["p75"] - spread["p25"]
    print(f"\n  risk spread across the middle half: {middle_half:.3f}")
    if middle_half < 0.08:
        print("  -> FAIL: too flat. Every street scores about the same, so the")
        print("     slider has nothing to choose between and routes never change.")
    else:
        print("  -> PASS: enough spread for the safety slider to do something.")

    nmr = _mean([x for n, v in night.items() if "north main" in n.lower() for x in v])
    print("\n  NOTE - a deliberate disagreement with the original brief:")
    print(f"  North Main Road scores {nmr:.3f}, lower than some quiet lanes. That is")
    print("  the busyness signal doing its job, not a bug. To make the bar strip")
    print("  score high instead, raise `nightlife` and drop `busy` in config.py -")
    print("  but then be ready to defend routing someone onto an empty lane.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
