"""
Tests for the risk model.
"""

# WHAT TO TEST HERE:
# - a score never comes out below 0 or above 1, whatever you throw at it
# - an unlit alley next to a cluster of bars scores higher than a lit main
#   road next to a police station
# - street lighting makes no difference to the score at midday, and a clear
#   difference at midnight
# - a street with no nearby places at all lands near the neutral middle

from __future__ import annotations

from services.risk import BUCKETS, explain, risk_attribute
from tests.conftest import DEST, LANE, ORIGIN, ROAD


def test_scores_stay_between_zero_and_one(two_ways_home):
    """Whatever you throw at it, a risk score is a probability-shaped number."""
    for _u, _v, data in two_ways_home.edges(data=True):
        for bucket in BUCKETS:
            assert 0.0 <= data[f"risk_{bucket}"] <= 1.0


def test_unlit_lane_by_bars_beats_lit_road_by_police(two_ways_home):
    """The core claim of the whole model, stated as a test."""
    lane = two_ways_home.edges[ORIGIN, LANE, 0]["risk_night"]
    road = two_ways_home.edges[ORIGIN, ROAD, 0]["risk_night"]
    assert lane > road
    # And not by a hair - the slider needs something real to work with.
    assert lane - road > 0.2


def test_lighting_is_ignored_at_noon_and_counts_at_midnight(two_ways_home):
    """
    A street light does nothing at midday. This is the time-of-day model
    earning its keep: the gap between the two routes should widen after dark.
    """
    lane_day = two_ways_home.edges[ORIGIN, LANE, 0]["risk_day"]
    road_day = two_ways_home.edges[ORIGIN, ROAD, 0]["risk_day"]
    lane_night = two_ways_home.edges[ORIGIN, LANE, 0]["risk_night"]
    road_night = two_ways_home.edges[ORIGIN, ROAD, 0]["risk_night"]

    assert road_night < road_day          # being lit only helps after dark
    assert lane_night > lane_day          # bars only matter after dark
    assert (lane_night - road_night) > (lane_day - road_day)


def test_featureless_street_lands_near_neutral(bare_graph):
    """No tags, nothing nearby - the model should not invent an opinion."""
    risk = bare_graph.edges[10, 11, 0]["risk_night"]
    assert 0.3 < risk < 0.7


def test_risk_attribute_picks_the_right_bucket():
    assert risk_attribute(hour=13) == "risk_day"
    assert risk_attribute(hour=19) == "risk_evening"
    assert risk_attribute(hour=23) == "risk_night"
    assert risk_attribute(hour=3) == "risk_night"      # 3am is still night


def test_explain_gives_reasons_a_person_can_read(two_ways_home):
    reasons = explain(two_ways_home, ORIGIN, LANE, 0, "night")["because"]
    assert any("lane" in r or "service" in r for r in reasons)
    assert any("nightlife" in r for r in reasons)
