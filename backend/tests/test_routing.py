"""
Tests for the routing.
"""

# WHAT TO TEST HERE:
# - with the safety dial at zero, the safer route is exactly the fastest one
# - as the dial goes up, the safer route never gets riskier on average
# - the safer route is never shorter than the fastest route (if it is, the
#   maths is broken somewhere)
# - a deliberately risky street gets avoided once the dial is high enough -
#   this is the one that proves the whole idea works
# - asking for a route to a point outside the demo area gives a clear error,
#   not a silently wrong line

from __future__ import annotations

import networkx as nx
import pytest

from services.routing import fastest_weight, find_routes, for_search, tradeoff
from tests.conftest import DEST, LANE, ORIGIN, ROAD


def test_slider_at_zero_gives_the_fastest_route(two_ways_home):
    """With safety weighted at nothing, the two routes must be the same route."""
    result = find_routes(two_ways_home, ORIGIN, DEST, k=0.0, hour=23)
    assert result["identical"]
    assert result["safer"]["distance_m"] == result["fastest"]["distance_m"]


def test_raising_the_slider_reroutes_around_the_risky_lane(two_ways_home):
    """
    The test that proves the whole idea works.

    Not just "a route came back" - the route has to actually change, and change
    towards the road rather than the lane.
    """
    lazy = find_routes(two_ways_home, ORIGIN, DEST, k=0.0, hour=23)
    careful = find_routes(two_ways_home, ORIGIN, DEST, k=0.5, hour=23)

    assert not careful["identical"]
    assert careful["safer"]["distance_m"] > lazy["fastest"]["distance_m"]
    assert careful["safer"]["mean_risk"] < lazy["fastest"]["mean_risk"]


def test_more_safety_never_means_more_risk(two_ways_home):
    """Nudging the slider towards safety must never make things worse."""
    risks = [
        find_routes(two_ways_home, ORIGIN, DEST, k=k, hour=23)["safer"]["mean_risk"]
        for k in (0.0, 0.1, 0.3, 0.6, 1.0)
    ]
    assert risks == sorted(risks, reverse=True)


def test_safer_route_is_never_shorter_than_the_fastest(two_ways_home):
    """
    If this ever fails, the maths is broken somewhere: the fastest route is by
    definition the shortest one, so nothing can beat it on distance.
    """
    for k in (0.0, 0.25, 0.5, 0.75, 1.0):
        result = find_routes(two_ways_home, ORIGIN, DEST, k=k, hour=23)
        assert result["safer"]["distance_m"] >= result["fastest"]["distance_m"] - 0.01


def test_tradeoff_numbers_are_the_right_way_round(two_ways_home):
    result = find_routes(two_ways_home, ORIGIN, DEST, k=1.0, hour=23)
    numbers = tradeoff(result["fastest"], result["safer"])
    assert numbers["extra_distance_m"] > 0
    assert numbers["risk_reduction_pct"] > 0


def test_cost_is_proportional_to_distance_not_to_segment_count(two_ways_home):
    """
    Guards the multiplicative cost rule.

    One 300 m street must cost the same as three 100 m streets with the same
    risk. With the additive form it would cost three times as much, which is how
    the model ends up measuring how the map was typed up rather than danger.
    """
    from services.routing import safer_weight

    cost = safer_weight(k=1.0, risk_attr="risk_night")
    one_long = cost(None, None, {"length": 300.0, "risk_night": 0.8})
    three_short = sum(
        cost(None, None, {"length": 100.0, "risk_night": 0.8}) for _ in range(3)
    )
    assert one_long == pytest.approx(three_short)


def test_cost_function_survives_parallel_streets():
    """
    Guards the trap where the pathfinder hands the cost rule a bundle of streets
    instead of one. When that goes unnoticed every street silently costs 1 and
    the search quietly stops being about distance.
    """
    graph = nx.MultiDiGraph()
    graph.add_node(1, y=18.53, x=73.89)
    graph.add_node(2, y=18.54, x=73.89)
    graph.add_edge(1, 2, length=500.0, risk_night=0.2)   # the road
    graph.add_edge(1, 2, length=100.0, risk_night=0.9)   # the shortcut

    priced = for_search(graph, fastest_weight)(1, 2, graph[1][2])
    assert priced == 100.0, "should price the cheapest of the parallel streets"


def test_no_path_between_disconnected_halves():
    graph = nx.MultiDiGraph()
    graph.add_node(1, y=18.53, x=73.89)
    graph.add_node(2, y=18.54, x=73.90)
    with pytest.raises(nx.NetworkXNoPath):
        find_routes(graph, 1, 2, k=0.5, hour=23)


def test_routing_works_without_scikit_learn(two_ways_home, monkeypatch):
    """
    The one test that would have caught a real outage.

    osmnx matches a coordinate to the nearest street corner using
    scikit-learn's BallTree - but only declares scikit-learn as OPTIONAL. It
    was installed on the machine this was written on, so every test here
    passed and every local run worked. The deployed server, which installs
    only what requirements.txt names, returned an error for every single route
    request. A dependency the project did not know it had is invisible right
    up until it is missing.

    So: hide scikit-learn, exactly as the server has it, and route anyway. If
    anyone reaches for osmnx's own nearest-node lookup again, this fails here
    instead of in production.
    """
    import sys

    # Setting a module to None in sys.modules makes `import` of it raise,
    # which is what the server's Python does - it genuinely is not there.
    for name in ("sklearn", "sklearn.neighbors"):
        monkeypatch.setitem(sys.modules, name, None)

    with pytest.raises(ImportError):
        import sklearn  # noqa: F401

    from services.routing import NodeIndex

    nodes = NodeIndex(two_ways_home)
    start, distance = nodes.nearest(18.5300, 73.8900)
    assert start == ORIGIN
    assert distance < 5  # metres: it is the corner we asked for

    finish, _ = nodes.nearest(18.5320, 73.8900)
    result = find_routes(two_ways_home, start, finish, k=0.6, hour=23)
    assert not result["identical"]
    assert result["safer"]["distance_m"] > 0
