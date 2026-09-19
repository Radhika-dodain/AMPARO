"""
POST /route — the heart of the app. Two points in, two routes out.

This endpoint does no heavy lifting itself; it hands off to services/routing.py
and just shapes the answer. All it should contain is the plumbing.
"""

# WHAT GOES IN HERE:
# - take the request: start, end, safety weight (k), hour of day
# - snap both points to the nearest actual street corner on the map
# - ask the routing service for the fastest route and the safer route
# - for each route work out: total distance, average risk, worst risk
# - work out how much longer the safer route is, in metres and percent
# - hand back both routes as map lines with those numbers attached
# - if there is genuinely no walkable path between the two points, say so
#   clearly instead of returning an empty map
#
# KEEP IN MIND: if the two routes come back identical, that is not a bug —
# it means the fastest way was already the safest. The UI should say that
# rather than drawing one line on top of another and looking broken.

from __future__ import annotations

import networkx as nx
from fastapi import APIRouter, HTTPException, Request

from schemas import RouteLine, RouteRequest, RouteResponse, Tradeoff
from services import routing
from services.risk import BUCKETS
from config import settings

router = APIRouter(tags=["routing"])


@router.post("/route", response_model=RouteResponse)
def get_routes(payload: RouteRequest, request: Request) -> RouteResponse:
    state = request.app.state.amparo
    graph = state.graph

    origin = routing.snap_to_node(graph, payload.origin_lat, payload.origin_lon)
    destination = routing.snap_to_node(graph, payload.dest_lat, payload.dest_lon)

    if origin == destination:
        raise HTTPException(
            400,
            "Those two points snap to the same street corner - pick spots "
            "further apart.",
        )

    try:
        result = routing.find_routes(
            graph, origin, destination, k=payload.k, hour=payload.hour
        )
    except nx.NetworkXNoPath:
        # Say so plainly. An empty map with no explanation looks like a crash.
        raise HTTPException(
            404,
            "No walkable route between those two points. They may be on "
            "disconnected parts of the street network.",
        )
    except nx.NodeNotFound:
        raise HTTPException(404, "Could not find a street near one of those points.")

    fastest = result["fastest"]
    safer = result["safer"]

    return RouteResponse(
        fastest=RouteLine(**fastest),
        safer=RouteLine(**safer),
        tradeoff=Tradeoff(**routing.tradeoff(fastest, safer)),
        # Not a bug when true: the quickest way was already the least risky.
        # The frontend says so in words instead of drawing two identical lines.
        identical=result["identical"],
        k=payload.k,
        hour=payload.hour,
        time_of_day=settings.weights.bucket_for_hour(payload.hour),
    )
