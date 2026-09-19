"""
GET /safety/overlay — every street with its risk score, so the map can
colour the whole neighbourhood.

The one endpoint that can single-handedly make the app feel slow. There are
roughly 10,000-20,000 street segments in the demo area; building that list
fresh on every request and asking a phone to draw all of it is how you get a
laggy demo.
"""

# WHAT GOES IN HERE:
# - do NOT compute anything here — read the version that was built once at
#   startup and kept in memory
# - group streets into a handful of risk bands (e.g. low / medium / high /
#   severe) rather than sending a unique number per street; the map only
#   needs enough detail to pick a colour
# - optionally let the caller ask for only the risky streets, so a phone can
#   draw a light version
# - optionally accept an hour of day, because a street's risk changes after
#   dark and the overlay should match the routes being drawn on top of it
# - include a version marker that changes when a new report lands, so the
#   frontend knows to refetch instead of showing a stale map

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, Response

from config import settings

router = APIRouter(tags=["overlay"])


@router.get("/safety/overlay")
def safety_overlay(
    request: Request,
    hour: int = Query(default=21, ge=0, le=23),
    risky_only: bool = Query(default=False),
) -> Response:
    """
    Note the return type: a raw Response, not a dict.

    Handing FastAPI a dictionary would make it walk 20,000 streets and turn them
    into JSON text again on every single call. The text was already built once at
    startup, so this just posts it - no work happens in this function at all.
    """
    state = request.app.state.amparo
    bucket = settings.weights.bucket_for_hour(hour)

    try:
        payload = state.overlay.payload(bucket, risky_only=risky_only)
    except (KeyError, ValueError):
        raise HTTPException(503, "Safety overlay is not built yet.")

    return Response(
        content=payload,
        media_type="application/json",
        headers={
            # The version changes whenever a report shifts the scores, so the
            # frontend can tell stale from current without re-downloading.
            "X-Overlay-Version": str(state.overlay.version),
            "Cache-Control": "no-cache",
        },
    )


@router.get("/safety/places")
def safety_places(request: Request) -> dict:
    """
    The places the risk model is actually built on: police, hospitals and
    clinics on one side, bars and clubs on the other, plus the shops and cafes
    that count as "there are people about".

    Read straight off the cached file - the same one the scoring used, so what
    the map draws and what the model believes can never drift apart.

    This is the best answer to "is this made up?" there is. Being able to point
    at the actual police station that pulled a street's score down beats any
    amount of explaining.
    """
    from services import poi

    try:
        places = poi.load_pois()
    except FileNotFoundError:
        raise HTTPException(503, "Places cache missing. Run scripts/build_cache.py")

    return {
        "area": settings.area_name,
        "places": {
            name: [{"lat": lat, "lon": lon} for lat, lon in points]
            for name, points in places.items()
        },
        "counts": {name: len(points) for name, points in places.items()},
    }
