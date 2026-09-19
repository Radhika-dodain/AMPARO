# Build plan — stage 1 (working prototype)

Two weeks, one person. The order matters more than the dates: each stage
proves something the next one depends on.

## Day 1 — scaffold and get the map on disk

Confirm the demo area. Install the backend dependencies — the map/geometry
stack is the part most likely to fight you, so hit it on day one. Run
`scripts/build_cache.py` and get a real map file with real places in it.
`/health` should report a street count above zero.

## Day 2 — deploy a hello-world, before you have anything to lose

Push an almost-empty backend to your host and open the URL.

This sounds premature and it is the most important day on the list. The
map/geometry libraries are heavyweight and their install surprises are common.
You want to discover them with twelve days of slack, not one. The original
plan had deployment on day 13; that is backwards.

## Days 3–4 — the risk model, and prove it

Implement the scoring. Then run `scripts/validate_risk.py` and check the
scores of streets you personally know.

**This is the gate.** If the main road with the bar strip does not score
riskier than a quiet residential lane, tune the weights until it does. Nothing
built on top of a wrong risk model is worth anything, so do not move on until
this reads correctly.

## Days 5–6 — routing

Both cost functions, with the multiplicative form. Prove that raising the
slider actually reroutes around a street you know is risky — not just that it
returns a route, but that the route *changes*. Return the distance and risk
numbers.

## Day 7 — overlay and reports API

Precompute the overlay in bands at startup. Build the reports endpoints
including the feedback into the risk layer, and confirm with a test that
posting a report raises a nearby street's risk immediately.

## Days 8–10 — the frontend

Map with tiles and tap-to-set-points. Route lines. Risk overlay with a legend.
The planner panel with the slider and the tradeoff cards. The demo preset
button.

By the end of day 10 the core idea should be visible and clickable.

## Days 11–12 — the rest of the UI

Panic button, report form with the visible-change-after-submit sequence,
history list, time-of-day toggle. Test at phone width.

## Day 13 — ship it

Build the frontend into the backend's folder, deploy, open it on an actual
phone on mobile data. Not on your laptop, not on wifi — on a phone, cold.

## Day 14 — buffer and rehearse

Fix what the phone test found. Rehearse the pitch against a clock. Have
answers ready for the two questions you will definitely get: "is a bar really
dangerous?" and "how is this different from Google Maps?"

## Deliberately left for later

Off-route detection, accounts, live tracking, outside incident feeds, a mobile
app. All of them are real features. None of them make the core idea land any
harder, and each one is a way to run out of time.

## Things to decide, not guess

- The exact demo area, if not Koregaon Park
- Which emergency number to dial
- Whether reports need to survive a redeploy, or resetting each time is fine
  for a demo
