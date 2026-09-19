"""
The shapes of everything going in and out of the API.

Having these written down means a bad request gets rejected with a clear
message instead of blowing up somewhere deep inside the routing code, and the
frontend gets an auto-generated API doc page for free.
"""

# WHAT GOES IN HERE:
#
# Incoming:
# - RouteRequest: start point, end point, how strongly to favour safety (k),
#   and the hour of day. Validate that the points actually fall inside the
#   demo area — otherwise the app silently routes from the nearest corner and
#   nobody understands why the line looks wrong.
# - ReportRequest: location, category, optional description, anonymous session
#   id. Category must be one of a fixed list, not free text, or the data is
#   unusable for anything later.
#
# Outgoing:
# - RouteResponse: two routes as map lines, and for EACH one: distance, average
#   risk, worst risk, and how much longer the safer one is as a percentage.
#   That last set of numbers is the pitch ("+180 m, 34% less risk") — without
#   them the app has nothing to say.
# - ReportResponse / HealthResponse: straightforward.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from config import settings

TimeOfDay = Literal["day", "evening", "night"]


class RouteRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float

    # The slider, as the user left it. 0 = pure speed, 1 = pure safety.
    k: float = Field(default=settings.default_k, ge=0.0, le=1.0)

    # Hour of day, 0-23. Lighting and nightlife only weigh in when they matter.
    hour: int = Field(default=21, ge=0, le=23)

    @model_validator(mode="after")
    def both_points_inside_demo_area(self) -> "RouteRequest":
        """
        Reject points outside the demo area instead of quietly routing from
        wherever happens to be nearest.

        Without this the app silently snaps a tap in Mumbai to the corner of
        Koregaon Park closest to it, draws a perfectly reasonable-looking line,
        and leaves whoever is watching with no idea why it is wrong.
        """
        outside = [
            label
            for label, lat, lon in (
                ("origin", self.origin_lat, self.origin_lon),
                ("destination", self.dest_lat, self.dest_lon),
            )
            if not settings.bbox.contains(lat, lon)
        ]
        if outside:
            raise ValueError(
                f"{' and '.join(outside)} outside the demo area "
                f"({settings.area_name}). Supported bounds: "
                f"lat {settings.bbox.south}..{settings.bbox.north}, "
                f"lon {settings.bbox.west}..{settings.bbox.east}."
            )
        return self


class ReportRequest(BaseModel):
    lat: float
    lon: float

    # A fixed list, never free text. Free-text categories are unusable for
    # anything later - you cannot weight them, group them or chart them.
    category: str
    description: str = Field(default="", max_length=500)
    session_id: str = Field(default="", max_length=64)

    @field_validator("category")
    @classmethod
    def known_category(cls, value: str) -> str:
        allowed = settings.report_weights.categories
        if value not in allowed:
            raise ValueError(f"category must be one of: {', '.join(allowed)}")
        return value

    @model_validator(mode="after")
    def inside_demo_area(self) -> "ReportRequest":
        if not settings.bbox.contains(self.lat, self.lon):
            raise ValueError(
                f"Report location is outside the demo area ({settings.area_name})."
            )
        return self


class RouteLine(BaseModel):
    """One route: the line to draw, and the numbers that describe it."""

    kind: Literal["fastest", "safer"]
    coordinates: list[list[float]]
    distance_m: float
    walk_minutes: int
    mean_risk: float
    max_risk: float
    risk_band: str
    segments: int


class Tradeoff(BaseModel):
    """
    What the safer route costs and what it buys.

    This is the product. "+180 m, 34% lower risk" is the whole pitch in six
    words, and a route response without these numbers leaves the app with
    nothing to say about the two lines it just drew.
    """

    extra_distance_m: float
    extra_distance_pct: float
    extra_minutes: int
    risk_reduction_pct: float


class RouteResponse(BaseModel):
    fastest: RouteLine
    safer: RouteLine
    tradeoff: Tradeoff

    # True when the quickest way there was already the least risky. Not a bug,
    # and the app should say so in words rather than draw one line over another.
    identical: bool

    k: float
    hour: int
    time_of_day: TimeOfDay


class ReportRecord(BaseModel):
    id: int
    lat: float
    lon: float
    category: str
    description: str = ""
    session_id: str = ""
    created_at: str
    created_at_local: str


class ReportResponse(BaseModel):
    """
    Deliberately more than "saved".

    The frontend needs to show that something visibly happened, so it gets told
    how many streets moved and what the new overlay version is - enough to
    refetch the map and point at the change.
    """

    status: Literal["saved"] = "saved"
    report: ReportRecord
    streets_affected: int
    overlay_version: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    area: str
    nodes: int
    edges: int
    risk_scored: bool
    reports: int
    overlay_version: int
    emergency_number: str
    default_k: float
    categories: list[str]
    bbox: dict[str, float]

    # The demo button's known-good trip, so the frontend does not hardcode
    # coordinates of its own that then drift out of step with the backend.
    demo_route: dict[str, list[float]]
