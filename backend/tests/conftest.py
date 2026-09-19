"""
Shared fixtures.

The important choice here: the tests build their own tiny street map instead of
loading the real one. A hand-made map means a test can say "this lane is unlit
and next to a bar, that road is lit and next to a police station" and then
assert what must follow. Against real OSM data you can only assert vague things,
and the suite would need a network connection and 200 seconds to start.
"""

from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.poi import PoiIndex          # noqa: E402
from services.risk import score_graph      # noqa: E402

# Corner ids, and they have to be integers. osmnx's nearest-node lookup casts
# ids to int, because every real OpenStreetMap node id is a number - so a
# fixture with friendly string names like "A" blows up inside the library
# rather than in our code, which is a confusing way to spend an afternoon.
ORIGIN, LANE, ROAD, DEST = 1, 2, 3, 4


@pytest.fixture
def two_ways_home():
    """
    A -> B, two ways round, inside the demo bbox.

      via L: 320 m of unlit service lane, two bars on it
      via R: 520 m of lit main road, a police station and shops on it

    The whole point of the app in four streets.
    """
    graph = nx.MultiDiGraph(crs="epsg:4326")
    corners = {
        ORIGIN: (18.5300, 73.8900),
        LANE: (18.5310, 73.8890),
        ROAD: (18.5310, 73.8930),
        DEST: (18.5320, 73.8900),
    }
    for name, (lat, lon) in corners.items():
        graph.add_node(name, y=lat, x=lon)

    def link(u, v, length, highway, lit=None):
        extra = {"lit": lit} if lit else {}
        for a, b in ((u, v), (v, u)):
            graph.add_edge(a, b, length=length, highway=highway, **extra)

    link(ORIGIN, LANE, 160, "service")
    link(LANE, DEST, 160, "service")
    link(ORIGIN, ROAD, 260, "primary", lit="yes")
    link(ROAD, DEST, 260, "primary", lit="yes")

    places = {
        "protective": [[18.5310, 73.8931]],
        "nightlife": [[18.5310, 73.8889], [18.5311, 73.8890]],
        "busy": [[18.5310, 73.8932], [18.5311, 73.8933], [18.5309, 73.8929],
                 [18.5312, 73.8931], [18.5310, 73.8934]],
    }
    score_graph(graph, PoiIndex.build(places))
    return graph


@pytest.fixture
def bare_graph():
    """Two corners, one featureless street, nothing nearby. The neutral case."""
    graph = nx.MultiDiGraph(crs="epsg:4326")
    graph.add_node(10, y=18.5300, x=73.8900)
    graph.add_node(11, y=18.5310, x=73.8900)
    graph.add_edge(10, 11, length=110, highway="unclassified")
    graph.add_edge(11, 10, length=110, highway="unclassified")
    score_graph(graph, PoiIndex.build({"protective": [], "nightlife": [], "busy": []}))
    return graph
