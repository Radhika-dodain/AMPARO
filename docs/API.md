# API contract

The shapes the frontend and backend agree on. Write this down before either
side is built, so they can be built in either order.

## `GET /health`

Is the server up and did the map load?

Returns: status, area name, number of streets, whether risk scores are
present, number of stored reports.

The street count is the useful field. If it is 0, the map file never loaded
and everything downstream will fail confusingly.

## `POST /route`

Send: start latitude/longitude, end latitude/longitude, the safety weight `k`
(0 to 1), and the hour of day.

Get back: two routes, each as a drawable line, each with:

- total distance in metres
- estimated walking time
- average risk along the route
- worst risk along the route
- which kind it is: fastest or safer

Plus, comparing the two: how many metres longer the safer route is, that as a
percentage, and how much lower its risk is as a percentage.

**Those comparison numbers are the product.** "The safer route is 180 m longer
and cuts average risk 34%" is the sentence the whole pitch is built on. A
response without them leaves the app with nothing to say.

Errors: no walkable path between the points; a point outside the demo area
(say so plainly — do not silently route from the nearest corner).

## `GET /safety/overlay`

Every street with its risk, for colouring the map.

Optional: an hour of day, and a "risky streets only" flag for phones.

Returns streets grouped into a few risk bands rather than a unique number
each, plus a version marker that changes whenever a report shifts the scores,
so the frontend knows when to refetch.

Must be served from memory, built once at startup.

## `GET /safety/places`

The places the risk model is built from: police stations, hospitals and
clinics; bars and clubs; shops and cafes. Read straight off the same cached
file the scoring used, so what the map draws and what the model believes can
never drift apart.

This exists to be pointed at. "Why is this street green?" is best answered by
switching the layer on and showing the police post forty metres away.

It is also honest about the model's limits: it shows how *few* places there
are. Eight protective, six nightlife. That is the whole evidence base in this
area, and the interface should not pretend otherwise.

## `POST /reports`

Send: latitude, longitude, category (from a fixed list), optional description,
anonymous session id.

Saves the report, **then immediately raises the risk of nearby streets and
rebuilds the overlay**, so the very next route request already avoids the area.

Returns: confirmation, how many streets were affected, and the new overlay
version — so the frontend can refetch and visibly show that something
happened.

## `GET /reports`

Optional: a session id to filter to one user's reports, and a limit.

Returns reports newest first, with local timestamps.
