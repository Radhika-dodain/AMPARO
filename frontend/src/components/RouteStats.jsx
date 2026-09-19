// The strip of numbers that floats under the map, describing whichever route
// is currently selected.
//
// Every figure here comes straight off the route the backend returned. There
// is no arithmetic in this file on purpose: if a number on screen disagrees
// with the model, the bug should be in one place, not two.
//
// WHAT IS DELIBERATELY NOT HERE:
// A "lit streets" figure, which looks like the obvious fifth stat and is the
// one you must not show. Not one of the 974 streets in this area carries a
// lighting tag in the map data, so any percentage would be invented. The risk
// model reads lighting where it exists; here it does not exist, and the
// interface should not imply otherwise.

import { RISK_BANDS, ROUTE_STYLES } from '../constants';

function Stat({ value, label, tone }) {
  return (
    <div className="a-stat">
      <div className="a-stat-value" style={tone ? { color: tone } : undefined}>
        {value}
      </div>
      <div className="a-stat-label">{label}</div>
    </div>
  );
}

export default function RouteStats({ routes, selected }) {
  if (!routes) return null;

  const route = routes.identical ? routes.safer : routes[selected];
  if (!route) return null;

  const km = route.distance_m >= 1000;
  const distance = km
    ? `${(route.distance_m / 1000).toFixed(2)} km`
    : `${Math.round(route.distance_m)} m`;

  const bandColour = (RISK_BANDS[route.risk_band] || RISK_BANDS.moderate).colour;

  return (
    <div className="a-stats">
      <div
        className="a-stats-tag"
        style={{ background: ROUTE_STYLES[route.kind].colour }}
      >
        {routes.identical ? 'Only one way' : ROUTE_STYLES[route.kind].label}
      </div>

      <Stat value={distance} label="Distance" />
      <Stat value={`${route.walk_minutes} min`} label="At 4.8 km/h" />
      <Stat value={route.mean_risk.toFixed(2)} label="Mean risk" tone={bandColour} />
      <Stat value={route.max_risk.toFixed(2)} label="Worst stretch" />
      <Stat value={route.segments} label="Streets" />
    </div>
  );
}
