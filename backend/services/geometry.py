"""
Turns a route through the map into a line the map can draw, plus the small
distance helpers everything else borrows.
"""

# WHAT GOES IN HERE:
# - convert a sequence of street corners into a drawable line
# - convert a single street segment into a drawable line
# - real-world distance between two coordinates
# - a check for whether a coordinate falls inside the demo area
#
# THE ONE THAT LOOKS OBVIOUSLY WRONG ON SCREEN:
# A street is rarely straight. The map data stores the actual curve of each
# street, but the easy version of this code just draws a straight line from
# corner to corner - so routes visibly cut diagonally through buildings and
# across the bend of a road. Anyone looking at the screen notices in two
# seconds. Use each street's stored shape where it has one, and only fall
# back to a straight line where it does not.
#
# SECOND, SUBTLER ONE:
# Two corners can be joined by more than one street (a road and a footpath
# running alongside it). Do not blindly grab the first one - use the specific
# street the pathfinder actually chose, or you will report the wrong distance.

from __future__ import annotations

import math
from typing import Any, Callable, Iterable, Sequence

EARTH_RADIUS_M = 6_371_000.0

# Metres per degree of latitude. Longitude is handled separately because it
# shrinks as you move away from the equator - see local_metre_frame().
METRES_PER_DEG_LAT = 110_574.0
METRES_PER_DEG_LON_EQUATOR = 111_320.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Real-world distance between two coordinates, in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def local_metre_frame(ref_lat: float, ref_lon: float) -> Callable[[Any, Any], tuple]:
    """
    Returns a function that converts (lat, lon) into metres east/north of a
    reference point.

    This is the fix for the distance bug in the docstring above. One degree of
    longitude at Pune's latitude is about 105.5 km, not 111 km, so treating the
    two axes as interchangeable makes every distance wrong by around 5% - which
    matters a great deal when the model turns on "within 200 m" versus "within
    300 m". Squashing the east-west axis by cos(latitude) makes the two axes
    comparable, so ordinary straight-line distance in this frame is real metres.

    Works on single numbers or on whole numpy arrays.
    """
    lon_scale = METRES_PER_DEG_LON_EQUATOR * math.cos(math.radians(ref_lat))

    def project(lat, lon):
        x = (lon - ref_lon) * lon_scale
        y = (lat - ref_lat) * METRES_PER_DEG_LAT
        return x, y

    return project


def in_bbox(bbox, lat: float, lon: float) -> bool:
    """Is this coordinate inside the demo area?"""
    return bbox.contains(lat, lon)


def edges_along_path(
    graph, path: Sequence, weight: Callable[[Any, Any, dict], float] | None = None
) -> list[tuple[Any, Any, Any, dict]]:
    """
    Turn a list of street corners into the list of actual streets between them.

    This is the fix for the "subtler one" in the docstring above. A pathfinder
    hands back corners, not streets, and two corners can be joined by several
    streets at once - a road and the footway running alongside it. Grabbing the
    first one blindly reports the wrong length and the wrong risk. So we pick
    the same street the pathfinder itself would have picked: the cheapest one
    under the very same cost rule.

    Returns (from_node, to_node, edge_key, edge_data) for each hop.
    """
    chosen: list[tuple[Any, Any, Any, dict]] = []
    for u, v in zip(path, path[1:]):
        candidates = graph.get_edge_data(u, v)
        if not candidates:
            continue
        if weight is None:
            key, data = min(
                candidates.items(), key=lambda kv: kv[1].get("length", float("inf"))
            )
        else:
            key, data = min(candidates.items(), key=lambda kv: weight(u, v, kv[1]))
        chosen.append((u, v, key, data))
    return chosen


def _edge_coordinates(graph, u, v, data: dict) -> list[list[float]]:
    """
    One street as a list of [lon, lat] points, following its real shape.

    This is the fix for the "looks obviously wrong on screen" note above.
    Streets bend. The map data stores each street's real curve, and drawing a
    straight line corner-to-corner instead sends routes visibly slicing through
    buildings and across the bend of a road. Use the stored shape when there is
    one, and only fall back to a straight line when there is not.
    """
    start = [graph.nodes[u]["x"], graph.nodes[u]["y"]]
    end = [graph.nodes[v]["x"], graph.nodes[v]["y"]]

    shape = data.get("geometry")
    coords = list(getattr(shape, "coords", []) or [])
    if len(coords) < 2:
        return [start, end]

    points = [[float(x), float(y)] for x, y in coords]

    # The stored shape may run the other way round from the direction we are
    # walking. Flip it if its far end is nearer to where we started.
    head_gap = haversine_m(start[1], start[0], points[0][1], points[0][0])
    tail_gap = haversine_m(start[1], start[0], points[-1][1], points[-1][0])
    if tail_gap < head_gap:
        points.reverse()

    # Snap the ends to the actual corners so consecutive streets join up
    # cleanly instead of leaving hairline gaps on the map.
    points[0], points[-1] = start, end
    return points


def path_to_coordinates(graph, edges: Iterable[tuple]) -> list[list[float]]:
    """Stitch the chosen streets into one continuous [lon, lat] line."""
    line: list[list[float]] = []
    for u, v, _key, data in edges:
        points = _edge_coordinates(graph, u, v, data)
        if line and points and line[-1] == points[0]:
            points = points[1:]          # do not repeat the shared corner
        line.extend(points)
    return line


def edge_to_linestring(graph, u, v, data: dict) -> dict:
    """A single street as a drawable GeoJSON geometry, for the risk overlay."""
    return {"type": "LineString", "coordinates": _edge_coordinates(graph, u, v, data)}


def walking_minutes(distance_m: float, metres_per_minute: float = 80.0) -> int:
    """Rough walking time. 80 m/min is a normal unhurried pace (4.8 km/h)."""
    return max(1, round(distance_m / metres_per_minute))
