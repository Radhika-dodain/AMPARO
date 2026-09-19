"""
Amparo backend — the entry point.

This is the file uvicorn starts. It does four things, in this order:

1. Reads settings from .env (which area, which port, where the files are).
2. Loads the prebuilt street map off disk into memory. This happens ONCE,
   at startup, not per request — that is the whole reason the app feels fast.
3. Applies any incident reports people have submitted on top of the risk
   scores, so past reports still count after a restart.
4. Precomputes the colour overlay for the whole area and keeps it in memory,
   because rebuilding it per request means sending megabytes every time.

After that it plugs in the four groups of endpoints (health, route, overlay,
reports) and, if a built frontend exists, serves that too — so the whole app
lives at one URL with no cross-origin headaches.

If the map file is missing it should fail loudly with "run
scripts/build_cache.py first", NOT quietly start downloading the map.
"""

# WHAT GOES IN HERE:
# - create the FastAPI app, give it a title
# - a startup step that loads the graph, replays reports, builds the overlay,
#   and stashes all three somewhere every endpoint can reach
# - allow cross-origin requests only when the dev flag in .env is on
# - include the four routers from routers/
# - mount the built frontend last (it must be last, or it swallows the API URLs)

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import db
from config import settings
from routers import health, overlay, reports, route
from services import graph_build, poi, risk
from services.overlay_cache import OverlayCache
from services.report_feedback import ReportLayer


@dataclass
class AppState:
    """
    Everything loaded at startup, in one place, reachable from any endpoint via
    request.app.state.amparo.

    The street map is the expensive thing here and it is loaded exactly once.
    Every route request after that is pure arithmetic over something already in
    memory, which is the entire reason responses come back instantly.
    """

    graph: object = None
    poi_index: object = None
    report_layer: ReportLayer | None = None
    overlay: OverlayCache = field(default_factory=OverlayCache)
    startup_seconds: float = 0.0


def _boot(state: AppState) -> None:
    """The four startup steps, in the order the docstring above lays out."""
    started = time.perf_counter()

    # 1. Read the prebuilt map off disk. Never downloads - a missing cache is
    #    shouted about, not papered over.
    print(f"[amparo] loading street map for {settings.area_name} ...")
    state.graph = graph_build.load_graph()
    summary = graph_build.graph_summary(state.graph)
    print(f"[amparo]   {summary['nodes']} corners, {summary['edges']} streets")

    # 2. Score the streets, unless the cache already carries the scores.
    if summary["scored"]:
        print("[amparo]   risk scores came with the cache")
    else:
        print("[amparo]   no risk scores in the cache - scoring now")
        state.poi_index = poi.PoiIndex.build(poi.load_pois())
        risk.score_graph(state.graph, state.poi_index)
    print(f"[amparo]   night risk spread: {risk.distribution(state.graph, 'night')}")

    # 3. Replay every stored report on top, so reports still count after a
    #    restart rather than quietly vanishing.
    db.init_db()
    state.report_layer = ReportLayer(state.graph)
    stored = db.all_reports_for_scoring()
    affected = state.report_layer.rebuild(stored)
    print(f"[amparo]   replayed {len(stored)} reports, {affected} streets adjusted")

    # 4. Build the colour overlay now, so no request ever has to.
    state.overlay.build(state.graph)
    print(f"[amparo]   overlay ready: {state.overlay.summary()}")

    state.startup_seconds = round(time.perf_counter() - started, 2)
    print(f"[amparo] ready in {state.startup_seconds}s")


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = AppState()
        _boot(state)
        app.state.amparo = state
        yield

    app = FastAPI(
        title="Amparo API",
        description="Safety-aware walking navigation. Map your own safety.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Only while developing, when the frontend runs on its own port. In
    # production the backend serves the frontend itself, so requests are
    # same-origin and this is not needed at all.
    if settings.allow_dev_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # ---- how long browsers may keep things ----
    #
    # This matters more than it sounds, and it caused a real and very
    # confusing failure: after a deploy, someone who had visited before kept
    # being served the PREVIOUS version of the app out of their own browser
    # cache. The server was fixed, the new code was live, and their screen
    # still showed the old broken behaviour - which looks exactly like the
    # deploy not having worked.
    #
    # The two halves need opposite treatment:
    #
    #   /assets/...  the file name contains a hash of its contents, so a
    #                changed file is a different name. Those can be kept
    #                forever; they can never go stale.
    #
    #   index.html   the one file whose name never changes, and the file that
    #                says which assets to load. It must be re-checked every
    #                time, or a browser holding an old copy asks for asset
    #                names that no longer exist.
    @app.middleware("http")
    async def cache_rules(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path == "/" or path.endswith(".html"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response

    app.include_router(health.router)
    app.include_router(route.router)
    app.include_router(overlay.router)
    app.include_router(reports.router)

    # Mounted LAST, and it has to be. Mounting the frontend at "/" swallows
    # every URL underneath it, so anything registered after this point would
    # never be reached and the API would 404 for no visible reason.
    if settings.frontend_dist.is_dir() and any(settings.frontend_dist.iterdir()):
        app.mount(
            "/",
            StaticFiles(directory=settings.frontend_dist, html=True),
            name="frontend",
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=True)
