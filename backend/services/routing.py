"""
Finds the two routes. The trick the whole project rests on.

Same map, same algorithm, run twice - with two different definitions of what
a street "costs" you.

  Run 1:  cost = how long the street is                    -> fastest route
  Run 2:  cost = length, made worse by how risky it is     -> safer route

The slider the user drags is just how heavily the second run punishes risk.
Slide it up and the algorithm becomes willing to walk further to avoid a bad
lane.
"""

# WHAT GOES IN HERE:
# - snap a raw tapped coordinate to the nearest real street corner
# - the "fastest" cost rule: just the length
# - the "safer" cost rule: length multiplied by (1 + k * risk)
# - run the pathfinder twice and return both paths
# - a straight-line distance estimate to help the pathfinder aim, so it
#   explores less of the map and answers faster
#
# WHY MULTIPLIED AND NOT ADDED - the most important note in this file:
# OpenStreetMap chops one physical street into however many pieces it feels
# like. If you ADD a flat risk penalty per piece, a main road stored as 10
# short pieces gets punished 10 times while a dodgy lane stored as 1 long
# piece gets punished once - for the same walking distance. You would be
# measuring how the map was typed up, not how dangerous the street is.
# Multiplying makes the penalty proportional to how far you actually walk,
# which is what we meant all along. It also keeps the pathfinder's shortcut
# estimate valid, which keeps routing fast.
#
# ORDER OF WORK: fix this multiplication BEFORE optimising the colour overlay,
# because changing the cost rule changes what the overlay should show and you
# do not want to cache the wrong picture.

from __future__ import annotations

from typing import Any, Callable, Sequence

import networkx as nx
import numpy as np
from scipy.spatial import cKDTree

from config import band_for_risk, settings
from services.geometry import (
    edges_along_path,
    haversine_m,
    local_metre_frame,
    path_to_coordinates,
    walking_minutes,
)
from services.risk import risk_attribute


class NodeIndex:
    """
    Which street corner is nearest to a tapped point.

    Built once, at startup, over every corner in the map.

    THIS REPLACED osmnx's OWN nearest_nodes, FOR TWO REASONS.

    The first was a production outage. On an unprojected map - ours, in plain
    latitude and longitude - osmnx reaches for scikit-learn's BallTree. That is
    an optional dependency. It happened to be installed on the machine this was
    written on, so every test passed and every local run worked, and the
    deployed server returned a 500 for every single route request. Nothing in
    the code mentioned scikit-learn; it was a dependency the project did not
    know it had. Doing the lookup ourselves means the only things we need are
    the ones we wrote down.

    The second is that osmnx built a fresh tree over all the corners on EVERY
    call. This one is built once and reused, which is simply less work per
    request.

    The projection is the same local metre frame the risk model uses, so
    "nearest" means nearest in metres rather than nearest in degrees - which,
    this far from the equator, is not the same thing.
    """

    def __init__(self, graph):
        ref_lat, ref_lon = settings.bbox.center
        self.project = local_metre_frame(ref_lat, ref_lon)

        self.ids = list(graph.nodes)
        lats = np.array([graph.nodes[n]["y"] for n in self.ids], dtype=float)
        lons = np.array([graph.nodes[n]["x"] for n in self.ids], dtype=float)
        x, y = self.project(lats, lons)
        self.tree = cKDTree(np.column_stack([x, y]))

    def nearest(self, lat: float, lon: float):
        """The id of the closest street corner, and how far away it is in metres."""
        x, y = self.project(float(lat), float(lon))
        distance, position = self.tree.query([x, y])
        return self.ids[position], float(distance)


def fastest_weight(u, v, data: dict) -> float:
    """Cost of a street when all you care about is getting there: its length."""
    return float(data.get("length", 1.0))


def safer_weight(k: float, risk_attr: str) -> Callable[[Any, Any, dict], float]:
    """
    Cost of a street when you also care about risk:

        length * (1 + alpha * risk)

    MULTIPLIED, NOT ADDED - the reason is in the docstring at the top of this
    file, and it is the single most important line of maths in the project.
    An added penalty punishes a street once per piece it happens to be stored
    in, so a main road chopped into ten short pieces is punished ten times and
    a dodgy lane stored as one long piece is punished once, for the same walk.
    That measures how the map was typed up. Multiplying makes the penalty
    proportional to distance actually walked.

    It also keeps the cost of a street at or above its plain length, which is
    what lets the straight-line estimate below stay valid - so this is real A*,
    not a slow search that only looks like one.

    The slider hands us k from 0 to 1; alpha is what that means in the maths.
    """
    alpha = max(0.0, float(k)) * settings.safety_weight_max

    def weight(u, v, data: dict) -> float:
        length = float(data.get("length", 1.0))
        risk = float(data.get(risk_attr, data.get("risk", 0.5)))
        return length * (1.0 + alpha * risk)

    return weight


def for_search(graph, cost: Callable[[Any, Any, dict], float]):
    """
    Adapts one of the cost rules above for the pathfinder itself.

    Worth knowing, because getting this wrong fails silently rather than loudly:
    when two corners can be joined by several streets at once, the pathfinder
    does not hand the cost rule one street - it hands over all of them at once,
    as a bundle. A rule written to read a single street then finds no length in
    that bundle, quietly falls back to its default of 1, and every street in the
    city ends up costing exactly the same. The search still returns a route, so
    nothing looks broken; it has just stopped being about distance at all and
    become about counting corners.

    So: unwrap the bundle, price each street in it, and take the cheapest - the
    same street edges_along_path() will later pick out for measuring.
    """
    if not graph.is_multigraph():
        return cost

    def weight(u, v, bundle: dict) -> float:
        return min(cost(u, v, data) for data in bundle.values())

    return weight


def straight_line_to(graph, destination) -> Callable[[Any, Any], float]:
    """
    How far the crow flies from here to the destination, in metres.

    This is what turns the search into A* rather than a plain flood outwards.
    It never over-estimates - a street is never shorter than the straight line
    between its ends - so the route it finds is still the genuinely cheapest one,
    just found after looking at far less of the map.
    """
    dest_lat = graph.nodes[destination]["y"]
    dest_lon = graph.nodes[destination]["x"]

    def heuristic(node, _target) -> float:
        return haversine_m(
            graph.nodes[node]["y"], graph.nodes[node]["x"], dest_lat, dest_lon
        )

    return heuristic


def summarise(graph, path: Sequence, weight_fn, risk_attr: str) -> dict:
    """
    Measure a route: how far, how long, how risky.

    Mean risk is weighted by length, not a plain average. A plain average lets a
    two-metre stub of pavement count as much as a 300 m stretch of unlit lane,
    which would make the headline number nonsense.
    """
    edges = edges_along_path(graph, path, weight_fn)
    lengths = np.array([float(d.get("length", 0.0)) for *_r, d in edges])
    risks = np.array(
        [float(d.get(risk_attr, d.get("risk", 0.5))) for *_r, d in edges]
    )

    total = float(lengths.sum())
    mean_risk = float((risks * lengths).sum() / total) if total > 0 else 0.0
    max_risk = float(risks.max()) if len(risks) else 0.0

    return {
        "coordinates": path_to_coordinates(graph, edges),
        "distance_m": round(total, 1),
        "walk_minutes": walking_minutes(total),
        "mean_risk": round(mean_risk, 3),
        "max_risk": round(max_risk, 3),
        "risk_band": band_for_risk(mean_risk),
        "segments": len(edges),
    }


def find_routes(graph, origin, destination, k: float, hour: int) -> dict:
    """
    The whole trick, in one function: the same search, twice, over the same map,
    with two different ideas of what a street costs.
    """
    risk_attr = risk_attribute(hour=hour)
    heuristic = straight_line_to(graph, destination)
    safer_cost = safer_weight(k, risk_attr)

    fastest_path = nx.astar_path(
        graph, origin, destination, heuristic=heuristic,
        weight=for_search(graph, fastest_weight),
    )
    safer_path = nx.astar_path(
        graph, origin, destination, heuristic=heuristic,
        weight=for_search(graph, safer_cost),
    )

    fastest = summarise(graph, fastest_path, fastest_weight, risk_attr)
    safer = summarise(graph, safer_path, safer_cost, risk_attr)
    fastest["kind"] = "fastest"
    safer["kind"] = "safer"

    return {
        "fastest": fastest,
        "safer": safer,
        "identical": fastest_path == safer_path,
        "risk_attr": risk_attr,
    }


def tradeoff(fastest: dict, safer: dict) -> dict:
    """
    The numbers the whole pitch rests on: what the safer route costs you, and
    what it buys you.

    "+180 m, 34% lower risk" is the sentence. Without these the app is two
    lines on a map with nothing to say about them.
    """
    extra_m = safer["distance_m"] - fastest["distance_m"]
    extra_pct = (
        (extra_m / fastest["distance_m"] * 100.0) if fastest["distance_m"] else 0.0
    )
    risk_drop_pct = (
        (fastest["mean_risk"] - safer["mean_risk"]) / fastest["mean_risk"] * 100.0
        if fastest["mean_risk"]
        else 0.0
    )
    return {
        "extra_distance_m": round(extra_m, 1),
        "extra_distance_pct": round(extra_pct, 1),
        "risk_reduction_pct": round(risk_drop_pct, 1),
        "extra_minutes": max(0, safer["walk_minutes"] - fastest["walk_minutes"]),
    }
