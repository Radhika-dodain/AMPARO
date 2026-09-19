"""
GET /health — "is the thing alive and did it load the map?"

The first URL you open after any deploy. Cheap to call, and it answers the
only question that matters when something looks broken.
"""

# WHAT GOES IN HERE:
# - return: ok/not-ok, the area name, how many streets got loaded, whether
#   risk scores are present, and how many reports are stored
# - the street count is the useful bit — if it says 0 the map file never
#   loaded and everything downstream is going to fail confusingly

from __future__ import annotations

from fastapi import APIRouter, Request

import db
from config import settings
from schemas import HealthResponse
from services import graph_build

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    state = request.app.state.amparo
    summary = graph_build.graph_summary(state.graph)

    # The street count is the field to look at. Zero means the map never
    # loaded, and everything downstream will fail in confusing ways until that
    # is fixed - so say it plainly here rather than leaving it to be guessed.
    ok = summary["edges"] > 0 and summary["scored"]

    return HealthResponse(
        status="ok" if ok else "degraded",
        area=settings.area_name,
        nodes=summary["nodes"],
        edges=summary["edges"],
        risk_scored=summary["scored"],
        reports=db.count_reports(),
        overlay_version=state.overlay.version,
        emergency_number=settings.emergency_number,
        default_k=settings.default_k,
        categories=list(settings.report_weights.categories),
        demo_route={
            "origin": list(settings.demo_origin),
            "destination": list(settings.demo_dest),
        },
        bbox={
            "north": settings.bbox.north,
            "south": settings.bbox.south,
            "east": settings.bbox.east,
            "west": settings.bbox.west,
        },
    )
