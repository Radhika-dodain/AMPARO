// The map itself. Everything visual sits on top of this.
//
// WHAT GOES IN HERE:
// - set up the Leaflet map with free map tiles (no account, no key, nothing to
//   run out of during a demo)
// - centre it on the demo area and stop the user panning off to Antarctica
// - handle taps: first tap sets where you are, second sets where you are
//   going, third starts over
// - draw the start and end pins
// - hold the route lines, the risk overlay and the report pins as layers
// - credit OpenStreetMap in the corner - this is a licence requirement, not a
//   nicety
//
// THESE ARE REAL ROADS.
// The tiles are real OpenStreetMap data, and every line drawn on top comes
// from the backend's own street graph - the same 974 streets it scored and
// routed over. Nothing on this map is drawn by hand.
//
// TWO BASEMAPS, ONE SWITCH:
// "Streets" is the ordinary OpenStreetMap style - the map everybody already
// knows how to read. "Quiet" is a pale grey canvas that gets out of the way so
// the risk shading can be the loudest thing on screen. Neither needs an API
// key, which is the point: the hosted basemaps that look nicest now all want
// one, and CARTO writes "API KEY REQUIRED" across every tile if you go without.
//
// WHY THE LAYERS ARE STACKED THE WAY THEY ARE:
// Leaflet sorts overlays into "panes" by number, and the order here is the
// whole reason the map stays readable:
//
//   tiles (200)   the roads themselves, with no lettering on them
//   risk  (400)   our colour along each street, like a traffic layer
//   names (430)   street names, ABOVE the shading so they stay legible
//   routes (450)  the two answers, above everything - they are the point
//   markers (600) pins, above all of it
//
// Putting the shading over the names would bury them; putting the names over
// the routes would cut the route lines into dashes. This order is the one that
// works.

import { useEffect, useRef } from 'react';
import {
  MapContainer,
  Marker,
  Pane,
  TileLayer,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import L from 'leaflet';

import { BASEMAPS, MAP_LIMITS } from '../constants';
import RiskOverlay from './RiskOverlay';
import RouteLayer from './RouteLayer';
import SafetyPlaces from './SafetyPlaces';

const PANES = { risk: 400, names: 430, routes: 450 };

// ---------------------------------------------------------------------------
// Pins
// ---------------------------------------------------------------------------
// Drawn as HTML rather than image files so they match the rest of the app and
// need no extra download. Leaflet's built-in marker images break under a
// bundler anyway, so hand-made icons are the simpler road as well as the
// prettier one.

const startIcon = L.divIcon({
  className: 'a-pin-wrap',
  html: `<span class="a-pin a-pin-start"><span class="a-pin-pulse"></span><span class="a-pin-dot"></span></span>`,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

const endIcon = L.divIcon({
  className: 'a-pin-wrap',
  html: `<svg viewBox="0 0 44 52" width="34" height="40" aria-hidden="true">
    <path d="M 4 44 L 4 20 L 22 4 L 40 20 L 40 44 Z" fill="#FFFFFF" stroke="#23342C" stroke-width="3" stroke-linejoin="round"/>
    <path d="M -1 22 L 22 2 L 45 22" fill="none" stroke="#D9633F" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="16" y="29" width="12" height="15" rx="2" fill="#9BD6C6"/>
  </svg>`,
  iconSize: [34, 40],
  iconAnchor: [17, 40],
});

const reportIcon = L.divIcon({
  className: 'a-pin-wrap',
  html: `<svg viewBox="0 0 34 44" width="24" height="31" aria-hidden="true">
    <path d="M17 42 C 9 31, 3 25, 3 17 A 14 14 0 0 1 31 17 C 31 25, 25 31, 17 42 Z" fill="#D9433F" stroke="#FFFFFF" stroke-width="3.2" stroke-linejoin="round"/>
    <path d="M17 9 v11 M17 25 v2" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round"/>
  </svg>`,
  iconSize: [24, 31],
  iconAnchor: [12, 31],
});

// ---------------------------------------------------------------------------
// Behaviour helpers
// ---------------------------------------------------------------------------

/** Turns a tap anywhere on the map into "set my start" or "set my finish". */
function TapToSetPoints({ onPick }) {
  useMapEvents({
    click(event) {
      onPick({ lat: event.latlng.lat, lon: event.latlng.lng });
    },
  });
  return null;
}

/**
 * Zoom so both routes fit, but only when the trip itself changes.
 *
 * Deliberately NOT on every new answer. Dragging the slider re-fetches
 * constantly, and a map that re-zooms under your thumb each time is horrible
 * to use - so this watches the two endpoints, not the routes.
 */
function FitToTrip({ origin, dest }) {
  const map = useMap();
  const lastTrip = useRef('');

  useEffect(() => {
    if (!origin || !dest) return;
    const trip = `${origin.lat},${origin.lon},${dest.lat},${dest.lon}`;
    if (trip === lastTrip.current) return;
    lastTrip.current = trip;

    map.flyToBounds(
      L.latLngBounds([
        [origin.lat, origin.lon],
        [dest.lat, dest.lon],
      ]),
      // Capped well short of the maximum: these trips are only a few hundred
      // metres, and zooming all the way in leaves you looking at building
      // outlines with no idea where in the neighbourhood you are.
      { padding: [80, 80], maxZoom: 16, duration: 0.7 },
    );
  }, [map, origin, dest]);

  return null;
}

/** The round zoom and recentre buttons, bottom right, like every map app. */
function MapButtons({ home }) {
  const map = useMap();
  return (
    <div className="a-mapbtns">
      <button
        type="button"
        className="a-mapbtn"
        aria-label="Back to the demo area"
        onClick={() => map.flyTo([home.lat, home.lon], MAP_LIMITS.defaultZoom, { duration: 0.6 })}
      >
        <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
          <circle cx="10" cy="10" r="6.5" fill="none" stroke="currentColor" strokeWidth="2" />
          <circle cx="10" cy="10" r="2" fill="currentColor" />
          <path d="M10 1v2.5M10 16.5V19M1 10h2.5M16.5 10H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>
      <button type="button" className="a-mapbtn" aria-label="Zoom in" onClick={() => map.zoomIn()}>
        <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
          <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
      </button>
      <button type="button" className="a-mapbtn" aria-label="Zoom out" onClick={() => map.zoomOut()}>
        <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
          <path d="M4 10h12" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// The map
// ---------------------------------------------------------------------------

export default function MapView({
  bbox,
  origin,
  dest,
  routes,
  overlay,
  places,
  reports = [],
  layers,
  selected,
  onSelect,
  onPick,
}) {
  if (!bbox) return <div className="a-map-loading">Waking the map up…</div>;

  const base = layers.quiet ? BASEMAPS.quiet : BASEMAPS.streets;

  const centre = {
    lat: (bbox.north + bbox.south) / 2,
    lon: (bbox.east + bbox.west) / 2,
  };

  // Keep the user inside the area the backend can actually route in. Panning
  // to Mumbai and tapping there only earns a refusal, so do not offer it.
  const limit = L.latLngBounds(
    [bbox.south - 0.012, bbox.west - 0.012],
    [bbox.north + 0.012, bbox.east + 0.012],
  );

  return (
    <MapContainer
      className="a-map"
      center={[centre.lat, centre.lon]}
      zoom={MAP_LIMITS.defaultZoom}
      minZoom={MAP_LIMITS.minZoom}
      maxZoom={MAP_LIMITS.maxZoom}
      maxBounds={limit}
      maxBoundsViscosity={0.85}
      zoomControl={false}
      attributionControl
      scrollWheelZoom
    >
      {/* The map everybody already knows how to read, or the pale one that
          gets out of the way. `key` forces Leaflet to swap the layer rather
          than try to reuse it with a different URL template. */}
      <TileLayer
        key={base.label}
        url={base.url}
        subdomains={base.subdomains || 'abc'}
        attribution={base.attribution}
        maxZoom={base.maxZoom}
        className={base.className}
        detectRetina
      />

      <Pane name="a-risk" style={{ zIndex: PANES.risk }}>
        {layers.risk && <RiskOverlay overlay={overlay} onPick={onPick} />}
      </Pane>

      {/* The quiet basemap keeps its lettering in a separate layer, so it can
          be lifted ABOVE the risk shading - otherwise a coloured street buries
          its own name. The streets basemap has its labels baked in and needs
          nothing here. */}
      {base.labelsUrl && (
        <Pane name="a-names" style={{ zIndex: PANES.names }}>
          <TileLayer key={`${base.label}-labels`} url={base.labelsUrl} maxZoom={base.maxZoom} detectRetina />
        </Pane>
      )}

      <Pane name="a-routes" style={{ zIndex: PANES.routes }}>
        <RouteLayer routes={routes} selected={selected} onSelect={onSelect} />
      </Pane>

      {layers.places && <SafetyPlaces places={places} />}

      {origin && <Marker position={[origin.lat, origin.lon]} icon={startIcon} alt="Your start" />}
      {dest && <Marker position={[dest.lat, dest.lon]} icon={endIcon} alt="Where you are going" />}

      {reports.map((report) => (
        <Marker
          key={report.id}
          position={[report.lat, report.lon]}
          icon={reportIcon}
          alt={`Reported: ${report.category.replace(/_/g, ' ')}`}
        />
      ))}

      <TapToSetPoints onPick={onPick} />
      <FitToTrip origin={origin} dest={dest} />
      <MapButtons home={centre} />
    </MapContainer>
  );
}
