// The small key that explains what the two lines mean, and the sentence that
// keeps the whole app honest.
//
// Easy to skip and a mistake to skip: without it, a stranger looking at the
// map sees pretty colours and has no idea what they are being told.
//
// WHAT GOES IN HERE:
// - what each route line looks like
// - one plain sentence: these scores come from street type, lighting, and
//   what is nearby - not from crime reports
//
// The colour key for the streets themselves lives on the map, in MapControls,
// next to the switch that turns the shading on. A key belongs beside the thing
// it explains.
//
// The sentence at the bottom is not decoration and should not be quietly
// dropped to save space. The model is built on proxies; a user who reads
// "safer" as "safe" has been misled by us, and that is a real harm rather than
// a presentational one.

import { ROUTE_STYLES } from '../constants';

export default function Legend() {
  return (
    <div className="a-legend">
      <div className="a-legend-rows">
        <span className="a-legend-row">
          <svg viewBox="0 0 26 6" width="26" height="6" aria-hidden="true">
            <path d="M0 3 h26" stroke={ROUTE_STYLES.safer.colour} strokeWidth="6" strokeLinecap="round" />
          </svg>
          lower risk — solid
        </span>
        <span className="a-legend-row">
          <svg viewBox="0 0 26 6" width="26" height="6" aria-hidden="true">
            <path
              d="M0 3 h26"
              stroke={ROUTE_STYLES.fastest.colour}
              strokeWidth="6"
              strokeDasharray="7 5"
              strokeLinecap="round"
            />
          </svg>
          fastest — dashed
        </span>
      </div>

      <p className="a-honesty">
        Risk is scored from street type, what is nearby and how busy a place is —
        never from crime reports. Lower risk on the signals we can measure, not a
        promise of safety.
      </p>
    </div>
  );
}
