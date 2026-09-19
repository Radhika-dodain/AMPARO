"""
Run this ONCE on your own machine, then commit what it produces.

    python scripts/build_cache.py

It downloads the street map and the places-of-interest for the demo area,
scores every street, and writes the result to data/. That file gets committed
so the live server never has to download anything.

Why this is a separate script and not something the app does on startup: the
public map service rate-limits, is occasionally slow, and a free hosting plan
puts the app to sleep when idle. Combine those and the judge who opens your
link cold triggers a live download and watches a spinner. Commit the file.

Re-run this only when you change the demo area or the risk weights.
"""

# WHAT GOES IN HERE:
# - read the demo area from config
# - download the walking street network
# - download the protective / risky / busy places
# - score every street
# - save the map and the places to data/
# - print a summary: how many streets, how many of each kind of place, and
#   the spread of risk scores, so you can eyeball whether it looks sane

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings                      # noqa: E402
from services import graph_build, poi, risk      # noqa: E402


def main() -> int:
    started = time.perf_counter()
    print(f"Building the map cache for {settings.area_name}")
    print(f"  bbox: {settings.bbox}")

    print("\n[1/4] Downloading the walking street network (this is the slow bit) ...")
    graph = graph_build.download_graph()
    print(f"      {graph.number_of_nodes()} corners, {graph.number_of_edges()} streets")

    print("\n[2/4] Downloading the places that matter for safety ...")
    places = poi.download_pois()
    for category, points in places.items():
        print(f"      {category:11} {len(points)}")
    poi_path = poi.save_pois(places)
    print(f"      cached to {poi_path}")

    print("\n[3/4] Scoring every street ...")
    index = poi.PoiIndex.build(places)
    risk.score_graph(graph, index)
    for bucket in risk.BUCKETS:
        print(f"      {bucket:8} {risk.distribution(graph, bucket)}")

    print("\n[4/4] Saving ...")
    graph_path = graph_build.save_graph(graph)
    size_mb = graph_path.stat().st_size / 1_000_000
    print(f"      {graph_path}  ({size_mb:.1f} MB)")

    print(f"\nDone in {time.perf_counter() - started:.1f}s")
    print("\nNow commit both files in data/. A deploy without them downloads the")
    print("map live at startup from a rate-limited service, which is how a demo dies.")
    print("Next: python scripts/validate_risk.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
