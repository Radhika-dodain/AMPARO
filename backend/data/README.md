# data/

Generated files live here.

- `graph_cache.graphml` — the prebuilt, risk-scored street map.
  **This one is committed to the repo on purpose.** Without it, a fresh
  deploy downloads the map live from a rate-limited public service while
  someone watches a loading spinner. Produce it with
  `python scripts/build_cache.py`.

- `pois.json` — the cached places of interest (police, hospitals, bars,
  cafes). Also committed, same reason.

- `amparo.db` — the reports database. Created automatically on first run and
  **not** committed; it is user data and it resets on each deploy, which is
  fine for a demo.
