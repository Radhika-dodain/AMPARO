"""
The risk model. This is the actual idea.

Walks every street segment once and gives it a number between 0 and 1. That
number is stored on the street itself, so nothing gets recalculated when
someone asks for a route.
"""

# WHAT GOES IN HERE:
#
# THE RECIPE - start every street at 0.5 (neutral), then nudge:
# - narrow service lane / alley / track     -> riskier
# - proper residential or main road         -> safer
# - tagged as lit                           -> safer
# - tagged as unlit                         -> riskier
# - close to police / hospital / clinic     -> safer, fading out with distance
# - close to bars / pubs / clubs            -> riskier, fading out with distance
# - lots of shops and cafes around          -> safer ("eyes on the street")
# - finally, clamp the result to stay between 0 and 1
#
# TIME OF DAY:
# Street lighting is irrelevant at noon and nightlife is irrelevant at 3pm.
# Take an hour as input and scale the lighting and nightlife nudges by how
# much they should matter at that hour. This is a small amount of work and it
# makes the whole model considerably more believable.
#
# ALL THE WEIGHTS LIVE IN config.py, not here. You will be tuning them.
#
# THE VALIDATION STEP - DO NOT SKIP THIS:
# After scoring, print the risk of 5-10 streets you personally know. If the
# main road with the bar strip does not score riskier than a quiet residential
# lane, the numbers are wrong and everything built on top of this is
# decoration. Fix it here before writing another file.

from __future__ import annotations

import numpy as np

from config import RiskWeights, settings
from services.poi import PoiIndex

# Which bucket names exist, and the order to report them in.
BUCKETS = ("day", "evening", "night")


def risk_attribute(hour: int | None = None, bucket: str | None = None) -> str:
    """
    Which stored field holds the risk for this time of day.

    The scores for all three times of day are worked out once and kept on the
    street itself, so asking for a route at midnight is just reading a different
    field - no rescoring, no waiting.
    """
    bucket = bucket or settings.weights.bucket_for_hour(hour if hour is not None else 21)
    if bucket not in BUCKETS:
        raise ValueError(f"Unknown time of day {bucket!r}, expected one of {BUCKETS}")
    return f"risk_{bucket}"


def _edge_midpoints(graph) -> tuple[np.ndarray, np.ndarray, list[tuple]]:
    """A representative point per street - the middle of its real shape where it has one."""
    keys, lats, lons = [], [], []
    for u, v, k, data in graph.edges(keys=True, data=True):
        shape = data.get("geometry")
        point = None
        if shape is not None:
            try:
                point = shape.interpolate(0.5, normalized=True)
            except Exception:
                point = None
        if point is not None:
            lats.append(float(point.y))
            lons.append(float(point.x))
        else:
            lats.append((graph.nodes[u]["y"] + graph.nodes[v]["y"]) / 2)
            lons.append((graph.nodes[u]["x"] + graph.nodes[v]["x"]) / 2)
        keys.append((u, v, k))
    return np.asarray(lats), np.asarray(lons), keys


def _first(value):
    """OSM tags arrive as either a single value or a list of them."""
    if isinstance(value, (list, tuple)):
        return value[0] if value else ""
    return value if value is not None else ""


def _falloff(distances: np.ndarray, radius_m: float) -> np.ndarray:
    """1.0 right on top of the place, fading straight down to 0.0 at the radius."""
    with np.errstate(invalid="ignore"):
        strength = 1.0 - (distances / radius_m)
    return np.clip(np.nan_to_num(strength, nan=0.0, posinf=0.0), 0.0, 1.0)


def score_graph(
    graph,
    poi_index: PoiIndex,
    weights: RiskWeights | None = None,
) -> None:
    """
    Score every street, once, and store the pieces on the street itself.

    Each street keeps its ingredients separately rather than one final number:
    the road-type baseline, and one adjustment each for lighting, police and
    hospitals, nightlife, and busyness. Keeping them apart is what makes the
    time-of-day switch and the report feedback loop cheap - both just recombine
    ingredients that are already there.
    """
    weights = weights or settings.weights
    lats, lons, keys = _edge_midpoints(graph)
    if len(keys) == 0:
        return

    # --- Road type: the baseline every street starts from ---
    base = np.full(len(keys), weights.neutral)
    lit_adjust = np.zeros(len(keys))
    for i, (u, v, k) in enumerate(keys):
        data = graph.edges[u, v, k]

        highway = str(_first(data.get("highway"))).lower()
        if highway in settings.risky_highways:
            base[i] += weights.risky_highway
        elif highway in settings.safer_highways:
            base[i] += weights.safer_highway

        lit = str(_first(data.get("lit"))).lower()
        if lit == "yes":
            lit_adjust[i] = weights.lit_yes
        elif lit == "no":
            lit_adjust[i] = weights.lit_no
        # Absent is the common case in Indian OSM data: no nudge either way.
        # This is why lighting is a bonus signal here, not the backbone.

    # --- Nearby places ---
    protective_adjust = weights.protective * _falloff(
        poi_index.nearest_distance_m("protective", lats, lons),
        weights.protective_radius_m,
    )
    nightlife_adjust = weights.nightlife * _falloff(
        poi_index.nearest_distance_m("nightlife", lats, lons),
        weights.nightlife_radius_m,
    )

    # Busyness saturates: one lone cafe says little, five or more says "there
    # are people here". This is the "eyes on the street" counterweight that
    # stops the model shoving someone off a busy main road into an empty lane.
    busy_counts = poi_index.count_within_m("busy", lats, lons, weights.busy_radius_m)
    busy_adjust = weights.busy * np.clip(busy_counts / 5.0, 0.0, 1.0)

    for i, (u, v, k) in enumerate(keys):
        data = graph.edges[u, v, k]
        data["risk_base"] = float(base[i])
        data["adj_lit"] = float(lit_adjust[i])
        data["adj_protective"] = float(protective_adjust[i])
        data["adj_nightlife"] = float(nightlife_adjust[i])
        data["adj_busy"] = float(busy_adjust[i])
        data.setdefault("adj_reports", 0.0)

    recompute(graph, weights)


def recompute(graph, weights: RiskWeights | None = None) -> None:
    """
    Rebuild the three final scores from the ingredients already on each street.

    Called after scoring, and again every time a report shifts things. Cheap,
    because it is only arithmetic - no distances are measured again.

    Two scores are kept per time of day:
      risk_osm_*  - what open map data alone says. Never changes.
      risk_*      - that, plus what people have reported.

    Keeping the untouched version is what lets reports be recalculated from
    scratch instead of piling on top of each other forever.
    """
    weights = weights or settings.weights
    for _u, _v, data in graph.edges(data=True):
        base = data.get("risk_base", weights.neutral)
        for bucket in BUCKETS:
            lit_mult, nightlife_mult = weights.time_of_day[bucket]
            score = (
                base
                + lit_mult * data.get("adj_lit", 0.0)
                + nightlife_mult * data.get("adj_nightlife", 0.0)
                + data.get("adj_protective", 0.0)
                + data.get("adj_busy", 0.0)
            )
            osm_only = min(1.0, max(0.0, score))
            data[f"risk_osm_{bucket}"] = osm_only
            data[f"risk_{bucket}"] = min(
                1.0, max(0.0, osm_only + data.get("adj_reports", 0.0))
            )

    # A convenience copy for anything that just wants "the" risk. Night is the
    # honest default: this app exists for the walk home after dark.
    for _u, _v, data in graph.edges(data=True):
        data["risk"] = data["risk_night"]


def distribution(graph, bucket: str = "night") -> dict:
    """The spread of scores - what scripts/build_cache.py prints so you can eyeball it."""
    attr = risk_attribute(bucket=bucket)
    values = np.array(
        [d.get(attr, 0.0) for _u, _v, d in graph.edges(data=True)], dtype=float
    )
    if len(values) == 0:
        return {"count": 0}
    return {
        "count": int(len(values)),
        "min": round(float(values.min()), 3),
        "p25": round(float(np.percentile(values, 25)), 3),
        "median": round(float(np.median(values)), 3),
        "p75": round(float(np.percentile(values, 75)), 3),
        "max": round(float(values.max()), 3),
        "mean": round(float(values.mean()), 3),
    }


def explain(graph, u, v, k, bucket: str = "night") -> dict:
    """
    Why did this street score what it scored?

    Powers the map tooltip, and answers "is this made up?" far better than any
    amount of explaining does.
    """
    data = graph.edges[u, v, k]
    lit_mult, nightlife_mult = settings.weights.time_of_day[bucket]
    reasons = []
    if data.get("risk_base", 0.5) > settings.weights.neutral:
        reasons.append("narrow lane or service road")
    elif data.get("risk_base", 0.5) < settings.weights.neutral:
        reasons.append("proper road")
    if lit_mult and data.get("adj_lit", 0.0) < 0:
        reasons.append("lit")
    if lit_mult and data.get("adj_lit", 0.0) > 0:
        reasons.append("tagged unlit")
    if data.get("adj_protective", 0.0) < -0.01:
        reasons.append("police or hospital nearby")
    if nightlife_mult and data.get("adj_nightlife", 0.0) > 0.01:
        reasons.append("nightlife nearby")
    if data.get("adj_busy", 0.0) < -0.01:
        reasons.append("shops and cafes around")
    if data.get("adj_reports", 0.0) > 0.001:
        reasons.append("reported by users")
    return {
        "name": _first(data.get("name")) or "unnamed street",
        "highway": str(_first(data.get("highway"))),
        "length_m": round(float(data.get("length", 0.0)), 1),
        "risk": round(float(data.get(risk_attribute(bucket=bucket), 0.0)), 3),
        "risk_osm_only": round(float(data.get(f"risk_osm_{bucket}", 0.0)), 3),
        "because": reasons or ["nothing notable nearby"],
    }
