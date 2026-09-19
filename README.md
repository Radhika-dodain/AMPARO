# Amparo — "Map your own safety"

Safety-aware walking navigation. For any trip it returns **two routes on one map**:
the fastest one, and a safer one — plus the honest tradeoff between them
("+180 m, 34% lower risk"). A slider lets the user decide how much extra
walking safety is worth to them.

Demo area: **Koregaon Park, Pune** (swap one config value for any other area).

---

## How it works in one paragraph

Every street segment in the demo area gets a risk score from 0 to 1 *before*
anyone asks for a route — based on road type, street lighting tags, how close
police/hospitals are, and how close nightlife is. Then we run the same
routing algorithm (A*) twice over the same map: once where a street costs its
length, once where it costs its length multiplied by its risk. First run gives
the fastest route, second gives the safer one. Because scoring happens once at
startup, answers come back instantly.

## Stage 1 scope (what we're building first)

The working prototype:

- Backend serves a real risk-scored street graph and returns two routes
- Map draws both routes, coloured risk overlay, and the tradeoff numbers
- Safety slider, report form, panic button, time-of-day toggle
- Reports write back into the risk layer so routing actually changes
- One FastAPI process serves the built frontend — one URL, no CORS

Deliberately **not** in stage 1: accounts, live tracking, off-route detection,
external incident feeds, mobile app.

## Folder map

    backend/     FastAPI service — graph, risk scoring, routing, reports API
    frontend/    React + Vite + Leaflet map UI
    docs/        How it is put together, and the API contract
    DEPLOY.md    Putting it online, written for a first-timer

## Running it

    # backend
    cd backend
    pip install -r requirements.txt
    python scripts/build_cache.py      # one time — downloads + scores the map
    python scripts/validate_risk.py    # check the model before trusting it
    uvicorn main:app --reload

    # frontend, in a second terminal
    cd frontend
    npm install
    npm run dev                        # http://localhost:5173

For the real thing — one URL, no CORS — build the frontend into the backend
and run the backend alone:

    cd frontend && npm run build       # lands in backend/frontend_dist/
    cd ../backend && uvicorn main:app  # http://localhost:8000 serves everything

Before pushing anything: `npm run check` in frontend/ (lint, then build) and
`python -m pytest` in backend/.

## Decisions worth knowing before you touch anything

- **The map cache is committed to the repo, not gitignored.** A fresh deploy
  with no cache downloads the map live from a public server that rate-limits.
  That is how a demo dies. Commit `backend/data/graph_cache.graphml`.
- **Safer cost is multiplicative, not additive.** `length * (1 + k * risk)`,
  never `length + k * risk` — see docs/ARCHITECTURE.md for why.
- **Risk is a proxy, not crime data.** Always present a route as a tradeoff
  with numbers attached, never as a safety guarantee.
- **The map tiles need no API key, and that is not an accident.** The
  good-looking hosted basemaps (CARTO, Mapbox, Stadia) all want one now, and
  CARTO prints "API KEY REQUIRED" diagonally across every tile if you go
  without — which was discovered by trying it. We use plain OpenStreetMap, with
  a pale Esri canvas as the second option.
- **Lint before you build.** `npm run build` happily bundles a reference to a
  variable that does not exist and hands you a blank white page. `npm run lint`
  catches it in a second.

## Licence

MIT — see [LICENSE](LICENSE). Map data is © OpenStreetMap contributors under
the Open Database License; the risk scores derived from it are part of this
project.
