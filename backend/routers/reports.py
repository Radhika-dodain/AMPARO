"""
POST /reports and GET /reports — user-submitted incidents.

This is the feature that makes the app more than a clever algorithm: someone
reports a badly lit stretch, and the next person routing through gets sent
around it. That loop is the most compelling thing in the demo, so it has to
actually work end to end, not just save a row and stop.
"""

# WHAT GOES IN HERE:
#
# POST:
# - check the reported location is inside the demo area
# - check the category is one of the allowed ones
# - save it to the database
# - THEN — and this is the part that is easy to forget — immediately bump the
#   risk score of nearby streets in the in-memory map, and rebuild the colour
#   overlay, so the very next route request already routes around it
# - return the updated risk of the affected streets so the UI can show that
#   something visibly happened
#
# GET:
# - list reports, newest first
# - accept a session id so a user can ask for only their own
# - accept a limit so it doesn't dump thousands of rows at a phone

from __future__ import annotations

from fastapi import APIRouter, Query, Request

import db
from schemas import ReportRecord, ReportRequest, ReportResponse

router = APIRouter(tags=["reports"])


@router.post("/reports", response_model=ReportResponse)
def create_report(payload: ReportRequest, request: Request) -> ReportResponse:
    state = request.app.state.amparo

    # The location and category were already checked by the schema, so a bad
    # report never reaches this far.
    record = db.insert_report(
        lat=payload.lat,
        lon=payload.lon,
        category=payload.category,
        description=payload.description,
        session_id=payload.session_id,
    )

    # THE PART THAT IS EASY TO FORGET, and the reason this feature exists at all.
    # Saving the row is not the feature. Rebuild the report penalties over the
    # live map and rebuild the overlay, so the very next /route call already
    # walks around this spot. Without these two lines the form is a write-only
    # box and the most compelling thing in the demo does not happen.
    affected = state.report_layer.rebuild(db.all_reports_for_scoring())
    state.overlay.build(state.graph)

    return ReportResponse(
        report=ReportRecord(**record),
        streets_affected=affected,
        overlay_version=state.overlay.version,
    )


@router.get("/reports", response_model=list[ReportRecord])
def get_reports(
    session_id: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ReportRecord]:
    """Newest first. The limit stops this dumping thousands of rows at a phone."""
    return [ReportRecord(**row) for row in db.list_reports(session_id, limit)]
