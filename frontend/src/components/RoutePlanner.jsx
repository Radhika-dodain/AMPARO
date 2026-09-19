// The panel where the user sets up their trip and reads the answer.
//
// WHAT GOES IN HERE:
// - the start and end fields, filled by tapping the map, with a "use my
//   location" button and a swap button
// - a "demo" button that instantly loads a known-good pair of points, so a
//   live demo never depends on tapping accurately
// - one card per route showing: walking time, distance and mean risk
// - tapping a card selects that route on the map
// - a clear "start over" action
//
// THE TRADEOFF LINE IS THE PRODUCT. If those numbers are missing or vague,
// the app is just two lines on a map. It gets its own box, big type, and sits
// directly under the two cards it compares.
//
// The demo button is not a gimmick. Tapping two points accurately on a map
// while a room watches is a good way to lose thirty seconds and your thread,
// and the pair it loads was chosen by scanning every pair in the area for the
// clearest tradeoff.

import { Penguin } from './Illustrations';
import { RouteCard, TradeoffNote } from './TradeoffCard';

function Field({ tone, label, place, onClear }) {
  return (
    <div className="a-field">
      <span className={`a-field-dot a-dot-${tone}`} aria-hidden="true" />
      <span className="a-field-body">
        <span className="a-field-label">{label}</span>
        <span className={`a-field-value ${place ? '' : 'is-empty'}`}>
          {place ? `${place.lat.toFixed(5)}, ${place.lon.toFixed(5)}` : 'tap the map'}
        </span>
      </span>
      {place && (
        <button type="button" className="a-field-clear" onClick={onClear} aria-label={`Clear ${label}`}>
          <svg viewBox="0 0 14 14" width="12" height="12" aria-hidden="true">
            <path d="M2 2 L12 12 M12 2 L2 12" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          </svg>
        </button>
      )}
    </div>
  );
}

export default function RoutePlanner({
  origin,
  dest,
  routes,
  loading,
  error,
  selected,
  onSelect,
  onSwap,
  onClear,
  onClearOne,
  onDemo,
  onLocate,
  locating,
  locateError,
}) {
  const ready = Boolean(origin && dest);

  return (
    <div className="a-planner">
      <div className="a-card a-trip">
        <Field tone="start" label="From" place={origin} onClear={() => onClearOne('origin')} />
        <span className="a-trip-rule" aria-hidden="true" />
        <Field tone="end" label="To" place={dest} onClear={() => onClearOne('dest')} />

        <div className="a-trip-actions">
          <button type="button" className="a-mini" onClick={onLocate} disabled={locating}>
            {locating ? 'Finding you…' : 'Use my location'}
          </button>
          <button type="button" className="a-mini" onClick={onSwap} disabled={!ready}>
            Swap
          </button>
          <button type="button" className="a-mini" onClick={onClear} disabled={!origin && !dest}>
            Start over
          </button>
          <button type="button" className="a-mini is-loud" onClick={onDemo}>
            Demo trip
          </button>
        </div>

        {locateError && <p className="a-warn">{locateError}</p>}
      </div>

      {error && <p className="a-error">{error}</p>}

      {!ready && !error && (
        <div className="a-card a-empty">
          <Penguin width={52} />
          <div>
            <div className="a-empty-title">Two taps and you are away</div>
            <div className="a-empty-note">
              Tap the map for where you are, then where you are going. Or hit{' '}
              <b>Demo trip</b>.
            </div>
          </div>
        </div>
      )}

      {ready && (
        <>
          <div className={`a-routecards ${loading ? 'is-busy' : ''}`}>
            {routes && !routes.identical && (
              <RouteCard
                kind="fastest"
                route={routes.fastest}
                isSelected={selected === 'fastest'}
                onSelect={onSelect}
              />
            )}
            {routes && (
              <RouteCard
                kind="safer"
                route={routes.safer}
                isSelected={routes.identical || selected === 'safer'}
                onSelect={onSelect}
              />
            )}
            {!routes && loading && <div className="a-card a-skeleton">Working out both routes…</div>}
          </div>

          <TradeoffNote routes={routes} />
        </>
      )}
    </div>
  );
}
