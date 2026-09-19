// Colours in every street by how risky it scored. The layer that makes the
// idea visible in one glance.
//
// WHAT GOES IN HERE:
// - draw each street from the backend in its band's colour
// - hovering a street shows its score, so "is this made up?" gets answered by
//   pointing rather than explaining
// - clicking a street still sets your start or finish, like clicking anywhere
//   else on the map
//
// It reads like the traffic layer on a map everybody already knows - a colour
// laid along each road - which means nobody has to be taught what they are
// looking at. The difference is what the colour means.
//
// THE BUG THIS LAYER CAUSES IF YOU ARE NOT CAREFUL:
// Leaflet swallows a click on any interactive layer, so it never reaches the
// map underneath. Bind a popup to a thousand streets and you have quietly
// broken tap-to-set-your-start across most of the screen - because streets are
// exactly where people tap. It looks like the app ignoring you.
//
// So: risk lines show what they know on HOVER, and pass their clicks straight
// through to the map's own handler. Tapping always sets a point, everywhere,
// with no exceptions to explain.
//
// PERFORMANCE:
// There are around a thousand streets here, and the backend has already done
// the hard part: it groups them into four bands and hands over ready-made
// JSON, so this only has to pick four colours. The GeoJSON layer is rebuilt
// only when the backend's version number changes - see the `key` below, which
// is the whole trick. Without it Leaflet keeps the first batch of lines
// forever and a submitted report never visibly changes anything.

import { useEffect, useRef } from 'react';
import { GeoJSON } from 'react-leaflet';
import { bandColour } from '../constants';

const BASE_WEIGHT = 5;
const HOVER_WEIGHT = 9;

export default function RiskOverlay({ overlay, onPick }) {
  // A ref, not the prop straight through, and this one matters.
  //
  // onEachFeature runs ONCE per street, when the layer is built - so whatever
  // onPick looked like at that moment is what a thousand click handlers keep
  // forever. The app swaps onPick whenever the mode changes ("set my start"
  // versus "pin this report"), and the streets would go on calling the old
  // one: you would tap to report a spot and silently move your start point
  // instead. Reading through a ref means the handlers always call the current
  // one without the layer having to be rebuilt.
  const latest = useRef(onPick);
  useEffect(() => {
    latest.current = onPick;
  }, [onPick]);

  if (!overlay || !overlay.features || overlay.features.length === 0) return null;

  const style = (feature) => ({
    color: bandColour(feature.properties.band),
    weight: BASE_WEIGHT,
    opacity: 0.8,
    lineCap: 'butt',
    lineJoin: 'round',
  });

  const onEachFeature = (feature, layer) => {
    const { risk, band } = feature.properties;

    // A tooltip, not a popup: it follows the pointer, needs no dismissing, and
    // never steals the click.
    layer.bindTooltip(
      `<span class="a-tip-band">${band} risk</span>` +
        `<span class="a-tip-score">${Number(risk).toFixed(2)}</span>`,
      { className: 'a-tip', sticky: true, direction: 'top', opacity: 1 },
    );

    layer.on({
      mouseover: (event) => event.target.setStyle({ weight: HOVER_WEIGHT, opacity: 1 }),
      mouseout: (event) => event.target.setStyle({ weight: BASE_WEIGHT, opacity: 0.8 }),
      // Hand the click on to the map, so tapping a street does what tapping
      // anywhere else does.
      click: (event) => latest.current({ lat: event.latlng.lat, lon: event.latlng.lng }),
    });
  };

  return (
    <GeoJSON
      // Rebuild when the backend says the scores moved. A report raises the
      // risk of nearby streets and bumps this number, which is what makes the
      // map visibly change the moment somebody submits one.
      key={`overlay-${overlay.version}-${overlay.time_of_day}`}
      data={overlay}
      style={style}
      onEachFeature={onEachFeature}
    />
  );
}
