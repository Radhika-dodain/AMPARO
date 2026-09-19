// Draws the two routes on the map.
//
// WHAT GOES IN HERE:
// - a thick solid line for whichever route is selected, a thinner dashed one
//   for the other, so the choice is obvious at a glance
// - distinct colours, and they must not be mistakable for the risk overlay
//   colours underneath
// - clicking a line selects that route
// - a white casing under each line, the way a road atlas outlines a highway,
//   so a green route does not disappear the moment it crosses a park
//
// THE CASE THAT LOOKS LIKE A BUG BUT ISN'T:
// Sometimes the fastest route IS the safest one, and both lines land on top
// of each other. When that happens only one line is drawn, in green, and the
// panel says so in words - see TradeoffCard. Drawing two identical lines and
// leaving the user to wonder is the worse answer.
//
// The backend sends coordinates the way map files do, longitude first.
// Leaflet wants latitude first. That flip is the single most common way to
// end up with a route drawn in the Indian Ocean, so it happens once, here.

import { Polyline } from 'react-leaflet';
import { ROUTE_CASING, ROUTE_STYLES } from '../constants';

const toLatLng = (coordinates) => coordinates.map(([lon, lat]) => [lat, lon]);

function OneRoute({ route, kind, isSelected, onSelect }) {
  if (!route || !route.coordinates || route.coordinates.length < 2) return null;

  const look = ROUTE_STYLES[kind];
  const points = toLatLng(route.coordinates);

  // The unselected route steps back rather than disappearing: a little
  // thinner, a little paler, still clearly there and still clickable. You
  // should always be able to see what you turned down - at 55% opacity it read
  // as an artefact rather than a choice, so it sits at 80%.
  const weight = isSelected ? look.weight + 1 : look.weight;
  const opacity = isSelected ? 1 : 0.8;

  return (
    <>
      <Polyline
        positions={points}
        interactive={false}
        pathOptions={{
          color: ROUTE_CASING.colour,
          weight: weight + ROUTE_CASING.extraWeight,
          opacity: isSelected ? 0.95 : 0.75,
          lineCap: 'round',
          lineJoin: 'round',
        }}
      />
      <Polyline
        positions={points}
        eventHandlers={{ click: () => onSelect(kind) }}
        pathOptions={{
          color: look.colour,
          weight,
          opacity,
          dashArray: look.dash || undefined,
          lineCap: 'round',
          lineJoin: 'round',
          className: isSelected ? 'a-route a-route-on' : 'a-route',
        }}
      />
    </>
  );
}

export default function RouteLayer({ routes, selected, onSelect }) {
  if (!routes) return null;

  // Only one line to draw: the quickest way is already the least risky one.
  if (routes.identical) {
    return <OneRoute route={routes.safer} kind="safer" isSelected onSelect={onSelect} />;
  }

  // Draw the unselected one first so the selected one lands on top of it.
  const order =
    selected === 'fastest'
      ? [['safer', routes.safer], ['fastest', routes.fastest]]
      : [['fastest', routes.fastest], ['safer', routes.safer]];

  return (
    <>
      {order.map(([kind, route]) => (
        <OneRoute
          key={kind}
          kind={kind}
          route={route}
          isSelected={selected === kind}
          onSelect={onSelect}
        />
      ))}
    </>
  );
}
