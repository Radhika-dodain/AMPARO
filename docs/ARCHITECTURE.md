# How Amparo is put together

## The five layers

**1. Map data.** The walking street network for the demo area — every footpath
and road, as a web of corners joined by street segments — plus the places that
matter for safety: police stations, hospitals and clinics on one side; bars,
pubs and clubs on the other; cafes, restaurants and shops as a "there are
people around" signal. Downloaded once on a laptop, committed to the repo.

**2. Risk scoring.** Walks every street segment once and gives it a number
between 0 and 1. Starts at 0.5 and nudges: a narrow service lane pushes up, a
proper road pushes down, a lighting tag pushes down, being near police or a
hospital pushes down, being near a cluster of bars pushes up, being somewhere
busy pushes down. The result is stored on the street itself. Nothing is
recalculated per request — that is what makes responses feel instant.

**3. Routing.** A pathfinder needs a cost for each street. Run it twice with
two different definitions of cost: length alone gives the fastest route;
length made worse by risk gives the safer one. The slider is how heavy that
penalty is.

**4. The API.** One process holds the map in memory. `/route` returns both
lines. `/safety/overlay` returns every street with its risk band so the map
can colour them. `/reports` accepts incidents and feeds them back into the
risk layer. It also serves the built frontend, so there is one URL and no
cross-origin configuration.

**5. The map UI.** Draws OpenStreetMap tiles, the two routes in contrasting
colours, the risk overlay, the panic button and the report form.

## The five decisions that matter most

These are the ones that were wrong in the first draft of the plan. Each one
either breaks the build, breaks the demo, or breaks the story.

### 1. Commit the prebuilt map file

A deploy without it downloads the map live from a rate-limited public service
at startup. Free hosting sleeps after a few minutes idle, so the person who
opens your link cold triggers that download and watches a spinner. This is the
highest-value line in this document.

### 2. Multiply the risk penalty, do not add it

    safer cost = length * (1 + k * risk)      <- correct
    safer cost = length + k * risk            <- wrong

OpenStreetMap chops one physical street into however many pieces it feels
like. Adding a flat penalty per piece punishes a main road stored as 10 short
pieces ten times over, while a dodgy lane stored as one long piece is punished
once — for the same walking distance. The additive version is partly measuring
data-entry habits rather than danger. Multiplying makes the penalty
proportional to distance walked, which is what was meant, and keeps the
pathfinder shortcut estimate valid so routing stays fast.

Do this before caching the overlay, because it changes what the overlay should
show.

### 3. Tell the map loader that risk is a number

The map file format has no types — everything reloads as text. The loader
knows "length" is a number; it has never heard of our "risk" field. So the
first run works and the run after a restart crashes on number-plus-text. Say
so explicitly when loading.

### 4. Build the overlay once, in bands

There are roughly 10,000–20,000 street segments here. Building the overlay
fresh per request and asking a phone to draw every one of them individually is
a guaranteed lag spike. Build it at startup, group streets into a few risk
bands, and offer a light version.

### 5. Reports have to actually change the routing

The original plan described "reports raise risk on nearby streets" and shipped
a form that saved rows nothing ever read. This is the most compelling feature
in the whole project — report something, watch the colours change, watch the
route move — and it does not exist unless it is built deliberately.

## The weak spot to have an answer ready for

"Bars are dangerous" is the softest claim in the model, and someone will poke
it. A busy, lit pub street at 11pm is often safer than an empty residential
lane; a naive model routes a woman off the main road onto that empty lane,
which is the opposite of the intent.

Two mitigations, both cheap, both in the plan: a busyness signal from nearby
shops and cafes that lowers risk, and treating nightclubs differently from
cafes. Have the counterargument ready regardless.

## Correct maths on distances

Latitude and longitude are not the same size. One degree east at Pune's
latitude is about 105.5 km, not 111 km, and mixing the two axes makes
north-south and east-west distances non-comparable. With 200 m and 300 m
falloff radii in the model, a 5% error matters. Convert to real metres, or
scale the east-west axis, before measuring anything.

## Known small traps

- Timestamps: the database default is UTC, so Indian times display 5.5 hours
  off unless handled.
- "Tap to call" links do nothing on a laptop, so the panic button looks dead
  in a laptop demo. Show the number as copyable text too.
- Browser location only works over a secure connection, so testing on a phone
  via a local network address will be refused. Use the deployed URL or the
  demo preset points.
- Report categories must come from a fixed list, not free text, or the data is
  unusable later.
- Close database connections; leaked handles eventually take the server down.
- A route drawn corner-to-corner cuts through buildings. Use each street's
  stored shape.
