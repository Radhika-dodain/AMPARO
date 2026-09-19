// The slider that lets the user decide how much extra walking safety is worth.
//
// WHAT GOES IN HERE:
// - a slider labelled "faster" at one end and "safer" at the other
// - never show the raw number behind it - nobody knows what k = 0.7 means
// - tell the user what just happened as they drag: "you would walk 200 m
//   further"
// - hold off on asking the server for a new route until they pause, or you
//   fire a request for every pixel of movement (that waiting lives in
//   useRoutes, so this component can stay immediate and dumb)
//
// This is the part people reach for first when they try the app. It should
// feel immediate.
//
// SET YOUR EXPECTATIONS BEFORE YOU DEMO IT:
// This behaves like a switch, not a dial. On a real street network there are
// only ever a handful of sensible ways between two points, so the route holds
// still, flips to another corridor at some threshold, and then holds still
// again. That is the graph being honest, not the slider being broken - so the
// readout below reports what actually changed rather than pretending to slide.

export default function SafetySlider({ value, onChange, routes }) {
  const detoured = routes && !routes.identical;

  let readout;
  if (!routes) {
    readout = 'Pick a start and a finish to see the difference.';
  } else if (detoured) {
    const { extra_distance_m: extra, risk_reduction_pct: cut } = routes.tradeoff;
    readout = `At this setting you would walk ${Math.round(extra)} m further and cut risk ${cut}%.`;
  } else if (value < 35) {
    readout = 'Straight there. Nudge right to see what a detour would buy you.';
  } else {
    readout = 'No detour worth taking here — the quick way is already the calm way.';
  }

  return (
    <div className="a-card a-slider">
      <label className="a-slider-title" htmlFor="safety-weight">
        How much further would you walk?
      </label>

      <input
        id="safety-weight"
        className="a-range"
        type="range"
        min={0}
        max={100}
        step={5}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-valuetext={
          value < 35 ? 'Speed first' : value < 70 ? 'A short detour is fine' : 'Well off the bad streets'
        }
      />

      <div className="a-slider-ends">
        <span className="a-end-fast">get there fast</span>
        <span className="a-end-safe">stay off bad streets</span>
      </div>

      <p className="a-slider-readout" aria-live="polite">
        {readout}
      </p>
    </div>
  );
}
