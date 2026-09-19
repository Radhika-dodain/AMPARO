"""
Tests that the endpoints answer at all and in the right shape.
"""

# WHAT TO TEST HERE:
# - /health reports a street count above zero
# - /route returns two routes, each with distance and risk numbers attached
# - /safety/overlay answers fast and does not return a unique colour per
#   street
# - posting a report saves it, and the risk of a nearby street goes up
#   straight afterwards - the feedback loop, end to end
# - asking for reports with a session id returns only that session's reports

from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

import db as db_module
import main
from config import settings
from services.overlay_cache import OverlayCache
from services.report_feedback import ReportLayer


@pytest.fixture
def client(two_ways_home, tmp_path, monkeypatch):
    """
    The real app, wired to the hand-made four-street map and a throwaway
    database.

    Lifespan is skipped deliberately: it would load the real 974-street map off
    disk and write to the real reports database, which makes the suite slow and
    lets tests leave traces behind.
    """
    monkeypatch.setattr(
        db_module, "settings", dataclasses.replace(settings, db_path=tmp_path / "t.db")
    )
    db_module.init_db()

    app = main.create_app()
    state = main.AppState(graph=two_ways_home, overlay=OverlayCache())
    state.report_layer = ReportLayer(two_ways_home)
    state.overlay.build(two_ways_home)
    app.state.amparo = state
    return TestClient(app)


def test_health_reports_a_real_street_count(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["edges"] > 0          # zero here means the map never loaded
    assert body["risk_scored"] is True
    assert "poor_lighting" in body["categories"]


def test_route_returns_two_routes_with_numbers_attached(client):
    response = client.post(
        "/route",
        json={"origin_lat": 18.5300, "origin_lon": 73.8900,
              "dest_lat": 18.5320, "dest_lon": 73.8900, "k": 0.6, "hour": 23},
    )
    assert response.status_code == 200
    body = response.json()

    for kind in ("fastest", "safer"):
        route = body[kind]
        assert route["distance_m"] > 0
        assert 0.0 <= route["mean_risk"] <= 1.0
        assert len(route["coordinates"]) >= 2

    # The numbers the pitch is built on must actually be there.
    assert body["tradeoff"]["extra_distance_m"] > 0
    assert body["tradeoff"]["risk_reduction_pct"] > 0
    assert body["time_of_day"] == "night"


def test_route_outside_the_demo_area_is_refused_clearly(client):
    response = client.post(
        "/route",
        json={"origin_lat": 19.07, "origin_lon": 72.87,
              "dest_lat": 18.5320, "dest_lon": 73.8900},
    )
    assert response.status_code == 422
    assert "outside the demo area" in response.text


def test_overlay_is_banded_and_fast(client):
    """
    The overlay must hand out risk bands, not a unique number per street - and
    it must not be doing any work per request.
    """
    response = client.get("/safety/overlay?hour=23")
    assert response.status_code == 200
    body = response.json()

    assert body["type"] == "FeatureCollection"
    assert body["features"]
    bands = {f["properties"]["band"] for f in body["features"]}
    assert bands.issubset({"low", "moderate", "elevated", "high"})
    assert response.headers["X-Overlay-Version"] == str(body["version"])


def test_overlay_light_version_is_smaller(client):
    everything = client.get("/safety/overlay?hour=23").json()
    risky_only = client.get("/safety/overlay?hour=23&risky_only=true").json()
    assert len(risky_only["features"]) < len(everything["features"])


def test_overlay_changes_with_time_of_day(client):
    noon = client.get("/safety/overlay?hour=12").json()
    midnight = client.get("/safety/overlay?hour=23").json()
    assert noon["time_of_day"] == "day"
    assert midnight["time_of_day"] == "night"
    noon_risks = [f["properties"]["risk"] for f in noon["features"]]
    night_risks = [f["properties"]["risk"] for f in midnight["features"]]
    assert noon_risks != night_risks


def test_reporting_raises_risk_nearby_and_reroutes(client):
    """
    The feedback loop, end to end, in one test. This is the feature the pitch
    leans on hardest and the one the original plan never actually built, so it
    gets the most thorough test in the suite.
    """
    trip = {"origin_lat": 18.5300, "origin_lon": 73.8900,
            "dest_lat": 18.5320, "dest_lon": 73.8900, "k": 0.0, "hour": 23}

    before = client.post("/route", json=trip).json()
    version_before = client.get("/safety/overlay?hour=23").json()["version"]

    # Somebody reports the lane the fast route currently uses.
    posted = client.post(
        "/reports",
        json={"lat": 18.5310, "lon": 73.8890, "category": "assault",
              "description": "no lights at all", "session_id": "sess-1"},
    )
    assert posted.status_code == 200
    saved = posted.json()
    assert saved["status"] == "saved"
    assert saved["streets_affected"] > 0            # the map really moved
    assert saved["overlay_version"] > version_before  # and was rebuilt

    # Same trip, same slider: the fast route through the lane is now riskier.
    after = client.post("/route", json=trip).json()
    assert after["fastest"]["mean_risk"] > before["fastest"]["mean_risk"]


def test_reports_are_filtered_by_session(client):
    for session in ("sess-a", "sess-a", "sess-b"):
        client.post("/reports", json={"lat": 18.5310, "lon": 73.8890,
                                      "category": "isolated", "session_id": session})

    assert len(client.get("/reports?session_id=sess-a").json()) == 2
    assert len(client.get("/reports?session_id=sess-b").json()) == 1
    assert len(client.get("/reports").json()) == 3


def test_free_text_categories_are_refused(client):
    response = client.post(
        "/reports",
        json={"lat": 18.5310, "lon": 73.8890, "category": "spooky vibes"},
    )
    assert response.status_code == 422
    assert "category must be one of" in response.text


def test_reports_outside_the_area_are_refused(client):
    response = client.post(
        "/reports", json={"lat": 19.07, "lon": 72.87, "category": "theft"}
    )
    assert response.status_code == 422


def test_timestamps_are_shown_in_local_time(client):
    """Stored as UTC, displayed shifted - so nobody reads a report as 5.5 hours early."""
    client.post("/reports", json={"lat": 18.5310, "lon": 73.8890,
                                  "category": "theft", "session_id": "tz"})
    record = client.get("/reports?session_id=tz").json()[0]
    assert record["created_at"].endswith("+00:00")
    assert record["created_at_local"] != record["created_at"]
