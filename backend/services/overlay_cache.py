"""
The colour overlay for the whole neighbourhood, built once and kept in memory.

Done naively, "give me every street and its risk" means building a
multi-megabyte payload from scratch on every request and asking a phone to
draw 20,000 lines. That is a guaranteed lag spike in front of whoever is
watching.
"""

# WHAT GOES IN HERE:
# - build the overlay once at startup, right after the map is scored
# - keep prebuilt versions for a few times of day (day / evening / night)
#   rather than recomputing per request
# - group streets into risk bands so the map draws a handful of colours
#   instead of thousands of slightly different ones
# - offer a light version that only includes the riskier streets, for phones
# - a "rebuild me" function that the reports endpoint calls when a new report
#   changes the risk scores
# - a version counter that bumps on every rebuild, so the frontend can tell
#   whether what it is showing is stale

from __future__ import annotations

import json

from config import RISK_BANDS, band_for_risk, settings
from services.geometry import edge_to_linestring
from services.risk import BUCKETS

# Only streets at or above this count as "risky" for the light version a phone
# asks for. Roughly the top third of a typical neighbourhood.
RISKY_THRESHOLD = 0.55

# Five decimal places is about a metre on the ground. Anything beyond that is
# bytes down the wire for detail no screen can show.
COORD_PRECISION = 5


class OverlayCache:
    """
    The whole neighbourhood's risk colours, built once and handed out as
    pre-made JSON text.

    Two separate savings here, and the second is the one people miss. Building
    the list of 20,000 streets once instead of per request is the obvious half.
    The other half is that turning that list into JSON is itself slow - so we do
    that once too, and every request after is just handing over bytes that
    already exist.
    """

    def __init__(self) -> None:
        self.version = 0
        self._payloads: dict[tuple[str, bool], str] = {}
        self._counts: dict[str, dict[str, int]] = {}

    def build(self, graph) -> None:
        """Rebuild every variant. Called at startup and after a report lands."""
        self.version += 1
        self._payloads.clear()
        self._counts.clear()

        for bucket in BUCKETS:
            attr = f"risk_{bucket}"
            bands: dict[str, int] = {}
            full, risky = [], []

            for u, v, data in graph.edges(data=True):
                risk = round(float(data.get(attr, 0.5)), 3)
                band = band_for_risk(risk)
                bands[band] = bands.get(band, 0) + 1

                geometry = edge_to_linestring(graph, u, v, data)
                geometry["coordinates"] = [
                    [round(x, COORD_PRECISION), round(y, COORD_PRECISION)]
                    for x, y in geometry["coordinates"]
                ]
                feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {"risk": risk, "band": band},
                }
                full.append(feature)
                if risk >= RISKY_THRESHOLD:
                    risky.append(feature)

            self._counts[bucket] = bands
            for risky_only, features in ((False, full), (True, risky)):
                self._payloads[(bucket, risky_only)] = json.dumps(
                    {
                        "type": "FeatureCollection",
                        "area": settings.area_name,
                        "time_of_day": bucket,
                        "version": self.version,
                        "risky_only": risky_only,
                        "bands": [name for name, _ in RISK_BANDS],
                        "counts": bands,
                        "features": features,
                    },
                    separators=(",", ":"),
                )

    def payload(self, bucket: str, risky_only: bool = False) -> str:
        """The ready-made JSON for one variant. No work happens here."""
        if bucket not in BUCKETS:
            raise ValueError(f"Unknown time of day {bucket!r}")
        return self._payloads[(bucket, risky_only)]

    def summary(self) -> dict:
        return {
            "version": self.version,
            "variants": len(self._payloads),
            "bands": self._counts.get("night", {}),
            "bytes_night": len(self._payloads.get(("night", False), "")),
        }
