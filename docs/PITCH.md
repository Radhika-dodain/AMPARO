# Pitch notes

## The one-liner

Amparo answers a question navigation apps do not ask: not just how do I get
there fastest, but how do I get there more safely.

Tagline: **map your own safety.**

## Why it matters

India has no street-level open crime feed, so safety information never reaches
the one moment it would matter — choosing which street to walk down. That
affects anyone walking alone after dark: women, students, late-shift and gig
workers, newcomers with no local instinct for which lane to avoid. The current
alternative is guesswork: take a longer route blindly, pay for a cab you do
not need, or do not go.

## The 2-minute demo, in order

1. **The problem, in a sentence.** It is 11pm, she has to get home, there are
   two ways to go — one shorter, unlit, past a row of bars; one five minutes
   longer, lit, with a police post on the way. She already knows which one she
   wants. Her maps app does not. It only knows which one is shorter.

2. **Why.** Every navigation app takes distance, traffic and turns, and gives
   back one route. Lighting, isolation, help nearby, time of night — none of
   that is part of the maths at all.

3. **The idea.** Score every street 0 to 1. Find two routes instead of one.
   Show exactly what the safer one costs: 160 m more, risk down 38%. The user
   decides.

4. **How.** Same algorithm twice. First time a street costs its length, second
   time its length times its risk. Same map, same algorithm, two different
   questions. All the scoring happens once at startup, so answers are instant.
   The data is OpenStreetMap — free, public, no key.

5. **The prototype.** Show the routes. Click the fastest one and point out
   where it cuts through unlit lanes. Click the safer one and read out the
   tradeoff. Drag the slider and let them watch the route move. Flip to
   daytime and let them watch the risk map cool down. Then pick two fresh
   points to prove it is not a fixed demo. Finally submit a report and let
   them watch the map change and the route move — that is the closing move.

## Answer these before you are asked

**"Are not busy bar streets actually safer than empty lanes?"** Often yes, and
the model accounts for it — nearby shops and cafes count as a busyness signal
that lowers risk, and nightclubs are weighted differently from cafes. This is
the single most likely hard question in the room. Have the answer ready.

**"This is not crime data."** Correct, and we never claim it is. These are
proxy signals from open map data, and the app presents a tradeoff with numbers
attached rather than a safety guarantee. In a country with no street-level
crime feed, proxies are what exist.

**"Does it only work in Pune?"** Change one bounding box. Any city with map
coverage works — no retraining, no new data pipeline. And crowdsourced reports
mean coverage improves with use.

## Do not say

"Safe route." Say "lower risk on the signals we can measure." Over-trust is a
real harm here, not a presentation nicety.

## What the slides claim that the code must therefore do

Treat the slide deck as a build checklist. Three claims on it are not true
until they are built:

- reports raising risk and changing future routing
- the "+180 m, 34% lower risk" tradeoff numbers in the route response
- a penalty independent of how the map segments a street (the multiplicative
  cost)

If you pitch the feedback loop and someone asks to see it, it needs to work.
