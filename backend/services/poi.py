"""
Finds the places that make a street feel safer or riskier.

Three lists, all pulled from OpenStreetMap:
  Protective - police stations, hospitals, clinics
  Risky      - bars, pubs, nightclubs
  Busy       - cafes, restaurants, shops (see the note below)

Then it builds a lookup structure so that, for any street, we can instantly
ask "how far is the nearest one of these?" without measuring against every
single place one by one.
"""

# WHAT GOES IN HERE:
# - fetch each category of place for the demo area and cache it next to the
#   map file - same reasoning: never download live during a demo
# - build a fast nearest-neighbour lookup for each category
#
# THE DISTANCE BUG TO AVOID:
# Latitude and longitude are not the same size as each other. One step east
# is a shorter real-world distance than one step north, and the gap is about
# 5% at Pune's latitude. If you treat them as interchangeable, every distance
# is wrong - which matters a lot when the whole model turns on "within 200 m"
# vs "within 300 m". Either convert the coordinates to real metres first, or
# squash the east-west axis by the right factor before building the lookup.
#
# THE "BUSY" LIST AND WHY IT EXISTS:
# The weakest claim in this whole project is "bars are dangerous". A busy, lit
# pub street at 11pm is often safer than an empty residential lane - and a
# naive model would route someone off the main road onto that empty lane,
# which is the opposite of the point. So: count nearby cafes, restaurants and
# shops as a general "there are people around" signal that LOWERS risk, and
# treat nightclubs differently from cafes. Expect to be asked about this.

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import osmnx as ox
from scipy.spatial import cKDTree

from config import BBox, settings
from services.geometry import local_metre_frame
from services.graph_build import _bbox_kwargs

CATEGORIES = ("protective", "nightlife", "busy")


def _tags_for(category: str) -> dict:
    return {
        "protective": settings.protective_tags,
        "nightlife": settings.nightlife_tags,
        "busy": settings.busy_tags,
    }[category]


def _centroids(gdf) -> np.ndarray:
    """
    Reduce whatever OSM gave us - points, building outlines, whole campuses -
    to one (lat, lon) per place.

    Centroids of lat/lon shapes are geometrically wrong (the axes are different
    sizes), so project to a local metric grid first, then come back.
    """
    if gdf is None or len(gdf) == 0:
        return np.empty((0, 2))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            metric = gdf.to_crs(gdf.estimate_utm_crs())
            points = metric.geometry.centroid.to_crs(4326)
        except Exception:
            points = gdf.geometry.centroid
    lats = points.y.to_numpy(dtype=float)
    lons = points.x.to_numpy(dtype=float)
    keep = np.isfinite(lats) & np.isfinite(lons)
    return np.column_stack([lats[keep], lons[keep]])


def download_pois(bbox: BBox | None = None) -> dict[str, list[list[float]]]:
    """Fetch all three categories of place. Slow, network-bound, runs on your laptop."""
    bbox = bbox or settings.bbox
    found: dict[str, list[list[float]]] = {}
    for category in CATEGORIES:
        try:
            gdf = ox.features_from_bbox(
                tags=_tags_for(category),
                **_bbox_kwargs(ox.features_from_bbox, bbox),
            )
            found[category] = _centroids(gdf).tolist()
        except Exception as exc:
            # An empty category is survivable; a crashed build is not. A
            # neighbourhood genuinely may have no police station.
            print(f"  ! no {category} places found ({type(exc).__name__}: {exc})")
            found[category] = []
    return found


def save_pois(pois: dict, path: Path | None = None) -> Path:
    """Cache the places next to the map file, and commit them for the same reason."""
    path = Path(path or settings.poi_cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "area": settings.area_name,
        "bbox": [settings.bbox.north, settings.bbox.south,
                 settings.bbox.east, settings.bbox.west],
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "places": pois,
    }
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return path


def load_pois(path: Path | None = None) -> dict[str, list[list[float]]]:
    """Read the cached places. Never downloads - same reasoning as the map."""
    path = Path(path or settings.poi_cache_path)
    if not path.exists():
        raise FileNotFoundError(
            f"No places cache at {path}. Run:  python scripts/build_cache.py"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    places = payload.get("places", {})
    return {category: places.get(category, []) for category in CATEGORIES}


@dataclass
class PoiIndex:
    """
    Fast "how far is the nearest one?" and "how many are within X?" lookups.

    Built on a local metre grid, NOT on raw latitude/longitude - see the
    distance-bug note in the docstring at the top of this file. Straight-line
    distance in this grid is real metres, so a 200 m radius means 200 m in both
    directions instead of 200 m north and 190 m east.
    """

    trees: dict[str, cKDTree | None]
    counts: dict[str, int]
    project: object

    @classmethod
    def build(cls, pois: dict[str, list[list[float]]], bbox: BBox | None = None) -> "PoiIndex":
        bbox = bbox or settings.bbox
        ref_lat, ref_lon = bbox.center
        project = local_metre_frame(ref_lat, ref_lon)

        trees: dict[str, cKDTree | None] = {}
        counts: dict[str, int] = {}
        for category in CATEGORIES:
            points = np.asarray(pois.get(category) or [], dtype=float)
            counts[category] = len(points)
            if len(points) == 0:
                trees[category] = None
                continue
            x, y = project(points[:, 0], points[:, 1])
            trees[category] = cKDTree(np.column_stack([x, y]))
        return cls(trees=trees, counts=counts, project=project)

    def nearest_distance_m(self, category: str, lats, lons) -> np.ndarray:
        """Distance in metres to the closest place of this kind. Infinity if none exist."""
        lats = np.atleast_1d(np.asarray(lats, dtype=float))
        lons = np.atleast_1d(np.asarray(lons, dtype=float))
        tree = self.trees.get(category)
        if tree is None:
            return np.full(lats.shape, np.inf)
        x, y = self.project(lats, lons)
        distances, _ = tree.query(np.column_stack([x, y]))
        return distances

    def count_within_m(self, category: str, lats, lons, radius_m: float) -> np.ndarray:
        """
        How many places of this kind are within the radius.

        Used for the busyness signal, where the question is "are there people
        around?" - and one lone cafe is a very different answer from twelve.
        """
        lats = np.atleast_1d(np.asarray(lats, dtype=float))
        lons = np.atleast_1d(np.asarray(lons, dtype=float))
        tree = self.trees.get(category)
        if tree is None:
            return np.zeros(lats.shape, dtype=int)
        x, y = self.project(lats, lons)
        neighbours = tree.query_ball_point(np.column_stack([x, y]), r=radius_m)
        return np.array([len(n) for n in neighbours], dtype=int)

    def summary(self) -> dict[str, int]:
        return dict(self.counts)
