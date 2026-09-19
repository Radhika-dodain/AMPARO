"""
Closes the loop: a submitted report actually changes where people get routed.

This is what turns a static model into something that improves with use, and
it is the single most compelling thing to show live. It is also the bit the
original plan described but never built - the report form saved rows into a
database that nothing ever read back.
"""

# WHAT GOES IN HERE:
# - given a reported location, find the street segments near it
# - raise their risk, most for the closest ones, fading out with distance
# - different categories carry different weight (poor lighting nudges gently,
#   a serious incident pushes hard)
# - older reports count for less than fresh ones, so one bad night does not
#   condemn a street forever
# - cap the total effect so one person spamming the form cannot rewrite the
#   whole map
# - keep the original OpenStreetMap-only score alongside the adjusted one, so
#   reports can be recalculated from scratch instead of stacking on top of
#   each other forever
# - a replay function that runs every stored report through this at startup,
#   so reports still count after a restart

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from scipy.spatial import cKDTree

from config import settings
from services.geometry import local_metre_frame
from services.risk import recompute


class ReportLayer:
    """
    Holds the extra risk that comes from what people have reported, kept apart
    from what the map data says.

    Built once over the street midpoints so that "which streets are near this
    report?" is instant, however many reports come in.
    """

    def __init__(self, graph):
        self.graph = graph
        ref_lat, ref_lon = settings.bbox.center
        self.project = local_metre_frame(ref_lat, ref_lon)

        self.keys: list[tuple] = []
        lats, lons = [], []
        for u, v, k, data in graph.edges(keys=True, data=True):
            shape = data.get("geometry")
            point = None
            if shape is not None:
                try:
                    point = shape.interpolate(0.5, normalized=True)
                except Exception:
                    point = None
            if point is not None:
                lats.append(float(point.y))
                lons.append(float(point.x))
            else:
                lats.append((graph.nodes[u]["y"] + graph.nodes[v]["y"]) / 2)
                lons.append((graph.nodes[u]["x"] + graph.nodes[v]["x"]) / 2)
            self.keys.append((u, v, k))

        if self.keys:
            x, y = self.project(np.asarray(lats), np.asarray(lons))
            self.tree = cKDTree(np.column_stack([x, y]))
        else:
            self.tree = None

    def _age_factor(self, created_at: str | None) -> float:
        """
        Last night counts more than last month.

        Halves every half_life_days, so one bad night does not condemn a street
        forever - but a street people keep reporting stays flagged.
        """
        if not created_at:
            return 1.0
        try:
            when = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except ValueError:
            return 1.0
        age_days = max(0.0, (datetime.now(timezone.utc) - when).total_seconds() / 86400)
        return float(0.5 ** (age_days / settings.report_weights.half_life_days))

    def rebuild(self, reports: list[dict]) -> int:
        """
        Work out every street's report penalty from scratch, then fold it in.

        From scratch on purpose. Adding each new report on top of whatever was
        there before means the numbers only ever climb and can never be undone -
        so instead the map-data-only score is kept untouched (risk_osm_*) and the
        report penalty is recalculated in full every time. Delete a report and
        the map really does go back.

        Returns how many streets ended up affected.
        """
        weights = settings.report_weights
        penalty = np.zeros(len(self.keys))

        if self.tree is not None:
            for report in reports:
                lat, lon = report.get("lat"), report.get("lon")
                if lat is None or lon is None:
                    continue
                x, y = self.project(float(lat), float(lon))
                nearby = self.tree.query_ball_point([x, y], r=weights.radius_m)
                if not nearby:
                    continue

                strength = weights.category_weight.get(
                    report.get("category", "other"),
                    weights.category_weight["other"],
                ) * self._age_factor(report.get("created_at"))

                points = self.tree.data[nearby]
                distances = np.hypot(points[:, 0] - x, points[:, 1] - y)
                # Full strength right at the report, fading to nothing at the edge
                falloff = np.clip(1.0 - distances / weights.radius_m, 0.0, 1.0)
                penalty[nearby] += strength * falloff

        # One person hammering the form must not be able to rewrite the map.
        penalty = np.clip(penalty, 0.0, weights.max_total_adjustment)

        affected = 0
        for i, (u, v, k) in enumerate(self.keys):
            value = float(penalty[i])
            self.graph.edges[u, v, k]["adj_reports"] = value
            if value > 0.001:
                affected += 1

        recompute(self.graph)
        return affected

    def streets_near(self, lat: float, lon: float, radius_m: float | None = None) -> list[dict]:
        """
        Which streets a report just touched, and what their risk is now.

        Handed straight back to whoever submitted, so the app can show that
        something visibly happened rather than just saying "saved".
        """
        if self.tree is None:
            return []
        radius_m = radius_m or settings.report_weights.radius_m
        x, y = self.project(float(lat), float(lon))
        touched = []
        for i in self.tree.query_ball_point([x, y], r=radius_m):
            u, v, k = self.keys[i]
            data = self.graph.edges[u, v, k]
            touched.append(
                {
                    "risk_night": round(float(data.get("risk_night", 0.0)), 3),
                    "added_by_reports": round(float(data.get("adj_reports", 0.0)), 3),
                }
            )
        return touched
