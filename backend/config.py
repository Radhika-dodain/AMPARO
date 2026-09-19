"""
One place for every setting. Nothing else in the codebase should read .env
directly — they all ask this file instead.

Why it matters: the demo area must be changeable by editing one line, not by
hunting for hardcoded coordinates scattered through the code. "Works in any
city with map coverage" is a big part of the pitch, and it stops being true
the moment someone types the coordinates inline.
"""

# WHAT GOES IN HERE:
# - load .env, fall back to sensible defaults so the app still runs without one
# - the demo bounding box, parsed from the DEMO_BBOX string into four numbers
# - the area's display name
# - file paths for the map cache and the reports database
# - the default safety-slider value
# - the emergency number
# - the dev-CORS on/off flag
# - the risk-model weights (see services/risk.py) kept here so they can be
#   tuned without touching logic

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Look for a .env next to the backend first, then at the project root.
for _candidate in (BACKEND_DIR / ".env", PROJECT_ROOT / ".env"):
    if _candidate.exists():
        load_dotenv(_candidate)
        break


def _env(key: str, default: str) -> str:
    value = os.getenv(key)
    return default if value is None or value == "" else value


def _env_float(key: str, default: float) -> float:
    try:
        return float(_env(key, str(default)))
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    return _env(key, "true" if default else "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass(frozen=True)
class BBox:
    """The demo area, as four edges. Parsed from DEMO_BBOX once, never inline."""

    north: float
    south: float
    east: float
    west: float

    @classmethod
    def parse(cls, raw: str) -> "BBox":
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 4:
            raise ValueError(
                f"DEMO_BBOX must be 'north,south,east,west' - got {raw!r}"
            )
        north, south, east, west = (float(p) for p in parts)
        if north <= south or east <= west:
            raise ValueError(
                f"DEMO_BBOX looks inside out: north must exceed south and "
                f"east must exceed west - got {raw!r}"
            )
        return cls(north=north, south=south, east=east, west=west)

    def contains(self, lat: float, lon: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lon <= self.east

    @property
    def center(self) -> tuple[float, float]:
        return ((self.north + self.south) / 2, (self.east + self.west) / 2)

    # osmnx 2.x wants (left, bottom, right, top); osmnx 1.x wanted the four
    # edges as separate arguments. services/graph_build.py handles both.
    def as_osmnx_tuple(self) -> tuple[float, float, float, float]:
        return (self.west, self.south, self.east, self.north)


@dataclass(frozen=True)
class RiskWeights:
    """
    Every knob in the risk model, in one place, so tuning never means editing
    logic. scripts/validate_risk.py is the thing that tells you whether these
    numbers are any good.
    """

    neutral: float = 0.5

    # Road type
    risky_highway: float = 0.15
    safer_highway: float = -0.10

    # Street lighting tag
    lit_yes: float = -0.15
    lit_no: float = 0.15

    # Nearby places, each fading linearly to zero at its radius
    protective: float = -0.20
    protective_radius_m: float = 300.0
    nightlife: float = 0.20
    nightlife_radius_m: float = 200.0

    # "Eyes on the street" - shops and cafes mean people around
    busy: float = -0.12
    busy_radius_m: float = 150.0

    # How much a time of day scales the two signals that depend on it.
    # (lighting_multiplier, nightlife_multiplier) per bucket.
    time_of_day: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "day": (0.0, 0.0),      # lighting and bars are irrelevant at noon
            "evening": (0.6, 0.5),
            "night": (1.0, 1.0),
        }
    )

    # Which hours belong to which bucket
    evening_starts_hour: int = 18
    night_starts_hour: int = 21
    day_starts_hour: int = 6

    def bucket_for_hour(self, hour: int) -> str:
        hour = int(hour) % 24
        if hour >= self.night_starts_hour or hour < self.day_starts_hour:
            return "night"
        if hour >= self.evening_starts_hour:
            return "evening"
        return "day"


@dataclass(frozen=True)
class ReportWeights:
    """How much a user report is allowed to move the map."""

    radius_m: float = 120.0
    max_total_adjustment: float = 0.35   # one street can never be pushed further
    half_life_days: float = 30.0         # yesterday counts more than last month

    category_weight: dict[str, float] = field(
        default_factory=lambda: {
            "poor_lighting": 0.10,
            "isolated": 0.10,
            "harassment": 0.22,
            "theft": 0.18,
            "assault": 0.30,
            "stray_dogs": 0.08,
            "unsafe_crossing": 0.08,
            "other": 0.10,
        }
    )

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(self.category_weight)


# Risk bands for the overlay. A street gets a band name, not a unique number,
# so the map draws four colours instead of twenty thousand.
RISK_BANDS: tuple[tuple[str, float], ...] = (
    ("low", 0.35),
    ("moderate", 0.50),
    ("elevated", 0.65),
    ("high", 1.01),
)


def band_for_risk(risk: float) -> str:
    for name, upper in RISK_BANDS:
        if risk < upper:
            return name
    return RISK_BANDS[-1][0]


@dataclass(frozen=True)
class Settings:
    port: int
    bbox: BBox
    area_name: str
    graph_cache_path: Path
    poi_cache_path: Path
    db_path: Path
    frontend_dist: Path
    default_k: float
    emergency_number: str
    allow_dev_cors: bool

    # The slider hands us 0..1. This is what 1.0 actually means inside the
    # cost function: at k=1 a maximally risky street costs 1 + this times its
    # length. Too small and the slider does nothing visible; too large and the
    # safer route wanders absurdly.
    safety_weight_max: float

    # Timestamps are stored as UTC and shifted by this for display. A fixed
    # offset on purpose: Windows has no system timezone database, so asking for
    # "Asia/Kolkata" by name needs an extra package and fails confusingly.
    display_utc_offset_hours: float

    weights: RiskWeights
    report_weights: ReportWeights

    # A known-good pair of points for the demo button. Found by scanning the
    # whole area for the trip with the best tradeoff, because hunting for a
    # good example by tapping the map while people watch is not a plan.
    demo_origin: tuple[float, float] = (18.538960, 73.897270)
    demo_dest: tuple[float, float] = (18.536561, 73.899698)

    # Which OpenStreetMap tags count as what. Kept here so a new city can be
    # tuned without touching services/poi.py.
    protective_tags: dict[str, list[str]] = field(
        default_factory=lambda: {"amenity": ["police", "hospital", "clinic"]}
    )
    # Note "bar": "yes". In Koregaon Park only four places carry
    # amenity=bar, while the actual drinking happens in venues tagged
    # amenity=restaurant with bar=yes hanging off them. Asking only for
    # amenity=bar finds almost none of the nightlife that exists.
    nightlife_tags: dict[str, object] = field(
        default_factory=lambda: {
            "amenity": ["bar", "pub", "nightclub", "biergarten", "stripclub"],
            "bar": "yes",
        }
    )
    busy_tags: dict[str, list[str]] = field(
        default_factory=lambda: {
            "amenity": ["cafe", "restaurant", "fast_food", "marketplace"],
            "shop": True,
        }
    )

    risky_highways: frozenset[str] = frozenset(
        {"service", "track", "path", "alley", "footway", "steps", "corridor"}
    )
    # Every highway type actually present in the area must appear in one list
    # or the other. A type in neither lands on exactly 0.5 and never moves,
    # which is how bridges ended up looking like the most dangerous places in
    # Koregaon Park: trunk roads were in neither list, so they kept the neutral
    # score while every real road was adjusted downwards around them.
    safer_highways: frozenset[str] = frozenset(
        {"primary", "secondary", "tertiary", "trunk", "residential",
         "living_street", "pedestrian", "unclassified",
         "primary_link", "secondary_link", "tertiary_link", "trunk_link"}
    )


def _env_pair(key: str, default: str) -> tuple[float, float]:
    lat, lon = (float(part) for part in _env(key, default).split(","))
    return (lat, lon)


def _resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else (BACKEND_DIR / path)


def load_settings() -> Settings:
    return Settings(
        port=int(_env_float("PORT", 8000)),
        bbox=BBox.parse(_env("DEMO_BBOX", "18.545,18.528,73.905,73.882")),
        area_name=_env("DEMO_AREA_NAME", "Koregaon Park, Pune"),
        graph_cache_path=_resolve(_env("GRAPH_CACHE_PATH", "data/graph_cache.graphml")),
        poi_cache_path=_resolve(_env("POI_CACHE_PATH", "data/pois.json")),
        db_path=_resolve(_env("DB_PATH", "data/amparo.db")),
        frontend_dist=_resolve(_env("FRONTEND_DIST", "frontend_dist")),
        default_k=_env_float("DEFAULT_K", 0.5),
        emergency_number=_env("EMERGENCY_NUMBER", "112"),
        allow_dev_cors=_env_bool("ALLOW_DEV_CORS", True),
        safety_weight_max=_env_float("SAFETY_WEIGHT_MAX", 6.0),
        display_utc_offset_hours=_env_float("DISPLAY_UTC_OFFSET_HOURS", 5.5),
        weights=RiskWeights(),
        report_weights=ReportWeights(),
        demo_origin=_env_pair("DEMO_ORIGIN", "18.538960,73.897270"),
        demo_dest=_env_pair("DEMO_DEST", "18.536561,73.899698"),
    )


# Import this, do not call load_settings() again all over the codebase.
settings = load_settings()
