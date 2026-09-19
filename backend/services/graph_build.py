"""
Gets the street map and keeps it on disk.

Downloads every footpath and road in the demo area from OpenStreetMap and
saves it as a file. This runs ONCE, on your laptop, and the result is
committed to the repo. It should never run on the live server during a demo.
"""

# WHAT GOES IN HERE:
# - download the walking street network for the demo bounding box
# - save it to disk as the map cache file
# - load it back from disk when the app starts
#
# TWO TRAPS, BOTH OF WHICH HAVE BITTEN THIS PROJECT BEFORE:
#
# 1. The library changed how you specify an area between versions. The old
#    way is a crash on line one with a fresh install. requirements.txt pins
#    the version that matches the code here - if you unpin it, fix this file.
#
# 2. The map file format has no concept of number vs text. Everything comes
#    back as text when you reload it. The built-in loader knows to turn
#    "length" back into a number, but it has never heard of our custom "risk"
#    field, so risk stays as text. Then the routing maths does number + text
#    and explodes. It works on the first run and dies after a restart, which
#    is the worst kind of bug. Tell the loader explicitly that risk is a
#    number.
#
# - also expose a "rebuild from scratch" path for when the demo area changes

from __future__ import annotations

import inspect
from pathlib import Path

import networkx as nx
import osmnx as ox

from config import BBox, settings

# Trap 2, made explicit. GraphML has no types: everything reloads as text.
# osmnx knows "length" is a number; it has never heard of our custom fields.
# Without this map, the first run works (real numbers in memory) and the run
# after a restart crashes doing number + text. Every float we invent must be
# listed here.
EDGE_DTYPES: dict[str, type] = {
    "length": float,
    "risk": float,
    "risk_day": float,
    "risk_evening": float,
    "risk_night": float,
    "risk_osm_day": float,
    "risk_osm_evening": float,
    "risk_osm_night": float,
    "risk_base": float,
    "adj_lit": float,
    "adj_protective": float,
    "adj_nightlife": float,
    "adj_busy": float,
    "adj_reports": float,
}

NODE_DTYPES: dict[str, type] = {"x": float, "y": float}


def _bbox_kwargs(func, bbox: BBox) -> dict:
    """
    Trap 1, handled rather than gambled on.

    osmnx 2.x takes one bbox tuple as (left, bottom, right, top). osmnx 1.x took
    north/south/east/west as four separate arguments - and note the order is not
    the same, so getting it wrong silently asks for a different patch of the
    planet rather than raising. Read the function's own signature and give it
    whichever form it actually wants.
    """
    params = inspect.signature(func).parameters
    if "bbox" in params:
        return {"bbox": bbox.as_osmnx_tuple()}
    return {
        "north": bbox.north,
        "south": bbox.south,
        "east": bbox.east,
        "west": bbox.west,
    }


def download_graph(bbox: BBox | None = None) -> nx.MultiDiGraph:
    """Fetch the walking street network for the demo area. Slow. Runs on your laptop."""
    bbox = bbox or settings.bbox
    graph = ox.graph_from_bbox(
        network_type="walk", simplify=True, retain_all=False,
        **_bbox_kwargs(ox.graph_from_bbox, bbox),
    )
    return graph


def save_graph(graph: nx.MultiDiGraph, path: Path | None = None) -> Path:
    """Write the scored map to disk. This file gets committed to the repo."""
    path = Path(path or settings.graph_cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, filepath=path)
    return path


def load_graph(path: Path | None = None) -> nx.MultiDiGraph:
    """
    Read the prebuilt map off disk.

    Deliberately does NOT fall back to downloading. A missing cache is a
    mistake to shout about at startup, not to paper over with a live fetch that
    leaves whoever opened the link staring at a spinner.
    """
    path = Path(path or settings.graph_cache_path)
    if not path.exists():
        raise FileNotFoundError(
            f"No street map at {path}.\n"
            f"Build it once with:  python scripts/build_cache.py\n"
            f"Then commit it - a deploy without this file downloads the map "
            f"live from a rate-limited public service at startup."
        )
    return ox.load_graphml(
        filepath=path, node_dtypes=NODE_DTYPES, edge_dtypes=EDGE_DTYPES
    )


def has_risk_scores(graph: nx.MultiDiGraph) -> bool:
    """Has this map already been scored, or is it raw OSM data?"""
    for _u, _v, data in graph.edges(data=True):
        return "risk_night" in data
    return False


def graph_summary(graph: nx.MultiDiGraph) -> dict:
    """Numbers worth printing after a build, and what /health reports."""
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "scored": has_risk_scores(graph),
    }
