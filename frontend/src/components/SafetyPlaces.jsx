// The places the risk model is actually built from: police stations, hospitals
// and clinics on one side, bars and clubs on the other.
//
// This layer exists to be pointed at. "Why is this street green?" is a fair
// question, and switching this on and showing the police post forty metres
// away answers it better than any amount of talking about weightings. It is
// also the honest half of the bargain: the same layer shows how FEW places
// there are, which is a real limit of the model and not worth hiding.
//
// The busy places - shops and cafes - are deliberately not drawn. There are a
// hundred and twenty-seven of them and they would bury the map; they are a
// background texture in the model, not a landmark.

import { CircleMarker, Popup } from 'react-leaflet';
import { PLACE_STYLES } from '../constants';

// Which categories get a dot, and what they are called in plain words.
const SHOWN = [
  { key: 'protective', title: 'Police, hospital or clinic', help: 'Lowers the risk of streets within 300 m.' },
  { key: 'nightlife', title: 'Bar or club', help: 'Raises the risk of streets within 200 m, after dark.' },
];

export default function SafetyPlaces({ places }) {
  if (!places || !places.places) return null;

  return (
    <>
      {SHOWN.map(({ key, title, help }) =>
        (places.places[key] || []).map((place, index) => (
          <CircleMarker
            key={`${key}-${index}`}
            center={[place.lat, place.lon]}
            radius={6}
            pathOptions={{
              color: '#FFFFFF',
              weight: 2.5,
              fillColor: PLACE_STYLES[key].colour,
              fillOpacity: 1,
            }}
          >
            <Popup className="a-pop-wrap" closeButton={false}>
              <div className="a-pop">
                <strong className="a-pop-band">{title}</strong>
                <span className="a-pop-note">{help}</span>
              </div>
            </Popup>
          </CircleMarker>
        )),
      )}
    </>
  );
}
