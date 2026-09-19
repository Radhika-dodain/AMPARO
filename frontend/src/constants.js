// The fixed values the UI reuses, in one place.
//
// WHAT GOES IN HERE:
// - the risk colour scale: which colour means low risk through to high.
//   Pick colours that stay readable for colour-blind users - green/red alone
//   is the one mistake everybody makes here.
// - the two route colours, chosen to be obviously different from each other
//   and from the risk overlay underneath
// - the report categories, matching exactly what the backend accepts
// - the time-of-day presets and which hour each one means
// - the slider's ends, labelled in plain words: "faster" on the left,
//   "safer" on the right - never show the user the raw number
// - a known-good pair of start/end points for the live demo, so you are never
//   hunting for a good example while people watch
//
// NOTE on that last one: the demo pair is NOT hardcoded here any more. The
// backend works it out and hands it over on /health, so the app and the map
// can never drift apart. See api.js.

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------
// Warm paper and leaf green, borrowed from field-journal illustration rather
// than from dashboard software. The map is the only cool thing on screen, so
// everything wrapped around it stays warm and keeps the eye pointed inward.
export const COLOURS = {
  paper: '#FBF6E9',
  paperEdge: '#E2DAC4',
  mint: '#E8F4E6',
  mintEdge: '#BEDDB4',
  panelEdge: '#E4EFDD',
  leaf: '#2F8B52',
  leafBright: '#4E9E63',
  deep: '#1B4E30',
  clay: '#D9633F',
  clayInk: '#B24A28',
  sun: '#F2C94C',
  sunPale: '#FFF7E2',
  sunEdge: '#EBCF8E',
  sunInk: '#7A5410',
  water: '#BCDFEE',
  alarm: '#D9433F',
  ink: '#23342C',
  muted: '#5E7A6C',
  faint: '#7C8F84',
  white: '#FFFFFF',
};

// ---------------------------------------------------------------------------
// Risk bands
// ---------------------------------------------------------------------------
// These four names come straight from the backend, which decides the band and
// sends it with every street. The frontend only picks the colour, so the two
// can never disagree about where a boundary sits.
//
// The ramp runs green -> yellow -> orange -> red, and the steps differ in
// lightness as well as hue, so it survives being seen by someone who cannot
// separate green from red.
export const RISK_BANDS = {
  low: { colour: '#7FB069', label: 'Low' },
  moderate: { colour: '#E9C46A', label: 'Moderate' },
  elevated: { colour: '#E08D4A', label: 'Elevated' },
  high: { colour: '#D9433F', label: 'High' },
};

export const BAND_ORDER = ['low', 'moderate', 'elevated', 'high'];

export function bandColour(band) {
  return (RISK_BANDS[band] || RISK_BANDS.moderate).colour;
}

// ---------------------------------------------------------------------------
// The two routes
// ---------------------------------------------------------------------------
// Different colour AND different dash. Colour alone is not enough: roughly one
// man in twelve cannot reliably separate these two hues, and this is the single
// most important distinction on the screen.
export const ROUTE_STYLES = {
  fastest: {
    label: 'Fastest',
    colour: '#D9633F',
    ink: '#B24A28',
    dash: '14 11',
    weight: 6,
  },
  safer: {
    label: 'Lower risk',
    colour: '#2F8B52',
    ink: '#1B4E30',
    dash: null,
    weight: 7,
  },
};

// White casing drawn under each route line, the way a road atlas outlines a
// highway. Without it a green route vanishes the moment it crosses a park.
export const ROUTE_CASING = { colour: '#FFFFFF', extraWeight: 5 };

// ---------------------------------------------------------------------------
// Report categories
// ---------------------------------------------------------------------------
// `id` must match the backend's list exactly - it rejects anything else, and
// rightly so: free-text categories cannot be weighted, grouped or charted.
export const REPORT_CATEGORIES = [
  { id: 'poor_lighting', label: 'Poor lighting' },
  { id: 'isolated', label: 'Felt isolated' },
  { id: 'harassment', label: 'Harassment' },
  { id: 'theft', label: 'Theft' },
  { id: 'assault', label: 'Assault' },
  { id: 'stray_dogs', label: 'Stray dogs' },
  { id: 'unsafe_crossing', label: 'Unsafe crossing' },
  { id: 'other', label: 'Something else' },
];

// ---------------------------------------------------------------------------
// Time of day
// ---------------------------------------------------------------------------
// The hour is what the backend actually wants; these three are just the
// friendly way of picking one. Night is the default everywhere in this app -
// it exists for the walk home after dark.
export const TIME_PRESETS = [
  { id: 'day', label: 'Day', hour: 12 },
  { id: 'evening', label: 'Evening', hour: 19 },
  { id: 'night', label: 'Night', hour: 23 },
];

export function presetForHour(hour) {
  if (hour >= 21 || hour < 6) return 'night';
  if (hour >= 18) return 'evening';
  return 'day';
}

// What time is it right now? Used to pick the opening state, so someone
// opening the app at 11pm sees the night map without touching anything.
export function currentPreset() {
  return presetForHour(new Date().getHours());
}

// ---------------------------------------------------------------------------
// The safety slider
// ---------------------------------------------------------------------------
// The user never sees the number. They see two ends and a sentence about what
// just changed.
export const SLIDER = {
  min: 0,
  max: 100,
  step: 5,
  start: 60,
  leftLabel: 'get there fast',
  rightLabel: 'stay off bad streets',
};

// ---------------------------------------------------------------------------
// Map places
// ---------------------------------------------------------------------------
// The things the risk model is actually built from, so a sceptic can be shown
// the police station that pulled a street's score down.
export const PLACE_STYLES = {
  protective: { colour: '#2F6FB0', label: 'Police, hospital, clinic' },
  nightlife: { colour: '#B5793A', label: 'Bar or club' },
  busy: { colour: '#7FB069', label: 'Shops and cafes' },
};

// ---------------------------------------------------------------------------
// Basemaps
// ---------------------------------------------------------------------------
// Two of them, both free and neither needing an API key - which is the whole
// reason this app cannot run out of anything halfway through a demo.
//
// WHY NOT THE USUAL SUSPECTS: the good-looking hosted basemaps (CARTO, Mapbox,
// Stadia) now all want a key, and CARTO stamps "API KEY REQUIRED" diagonally
// across every tile if you skip it. That is a spectacular way to ruin a demo,
// so both options below were checked by actually fetching a tile over
// Koregaon Park and looking at it.
//
//   streets - the standard OpenStreetMap style. The most familiar map there
//             is: white and yellow roads, green parks, blue water. It is
//             lightly desaturated in CSS (see .a-tiles-streets in styles.css)
//             so our route lines and risk colours sit on top of it rather
//             than fighting it.
//
//   quiet   - a very pale grey canvas with the lettering as its own layer.
//             Almost nothing on it competes for attention, so the risk
//             shading becomes the loudest thing on screen. This is the one to
//             switch to when you are explaining the model.
//
// Attribution is not decoration. Both of these require it, and Leaflet puts
// it in the corner automatically from the string below.
export const BASEMAPS = {
  streets: {
    label: 'Streets',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    subdomains: 'abc',
    maxZoom: 19,
    className: 'a-tiles-streets',
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
  quiet: {
    label: 'Quiet',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    labelsUrl:
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
    maxZoom: 16,
    className: '',
    attribution:
      'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors',
  },
};

// How far out the user may zoom before the demo area stops filling the screen.
export const MAP_LIMITS = { minZoom: 13, defaultZoom: 15, maxZoom: 19 };

export const EMERGENCY_FALLBACK = '112';
