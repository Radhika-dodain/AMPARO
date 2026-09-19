// One route, summarised. Used for both the fastest and the safer route.
//
// WHAT GOES IN HERE:
// - which route this is, in words, not jargon
// - walking time and distance
// - a risk reading shown as something human - a coloured bar and a word like
//   "moderate" - rather than "0.63"
// - for the safer route: how much further it is and how much less risky, side
//   by side, because that comparison is the entire pitch
// - selected styling, and a tap to select
//
// THE HONESTY RULE: never label a route "safe". It is "lower risk on the
// signals we can measure". The model uses proxies, not crime reports, and
// overclaiming is both wrong and the first thing a sharp judge will attack.
// That is why the card says "Lower risk" and never "Safe route".

import { RISK_BANDS, ROUTE_STYLES } from '../constants';

export function RouteCard({ route, kind, isSelected, onSelect }) {
  if (!route) return null;

  const look = ROUTE_STYLES[kind];
  const band = RISK_BANDS[route.risk_band] || RISK_BANDS.moderate;

  return (
    <button
      type="button"
      className={`a-card a-routecard ${isSelected ? 'is-on' : ''}`}
      style={isSelected ? { borderColor: look.colour } : undefined}
      aria-pressed={isSelected}
      onClick={() => onSelect(kind)}
    >
      <span className="a-routecard-head">
        <span className="a-swatch" style={{ background: look.colour }} />
        <span className="a-routecard-name">{look.label}</span>
        <span className="a-routecard-time">{route.walk_minutes} min</span>
      </span>

      <span className="a-routecard-dist">
        <b>{Math.round(route.distance_m)}</b> metres
      </span>

      <span className="a-routecard-risk">
        <span className="a-risk-label">risk</span>
        <span className="a-bar">
          <span
            className="a-bar-fill"
            style={{ width: `${Math.round(route.mean_risk * 100)}%`, background: band.colour }}
          />
        </span>
        <span className="a-risk-word">{band.label.toLowerCase()}</span>
      </span>
    </button>
  );
}

/**
 * The tradeoff itself. This little box is the product.
 *
 * "+80 m, risk down 43%" is the whole pitch in six words. If these numbers are
 * missing or vague, the app is just two lines on a map.
 */
export function TradeoffNote({ routes }) {
  if (!routes) {
    return (
      <div className="a-card a-trade is-quiet">
        <div className="a-trade-kicker">what it costs you</div>
        <div className="a-trade-line">Set a start and a finish to find out.</div>
      </div>
    );
  }

  if (routes.identical) {
    return (
      <div className="a-card a-trade is-quiet">
        <div className="a-trade-kicker">what it costs you</div>
        <div className="a-trade-line">
          Nothing. The quickest way here is already the calmest one.
        </div>
      </div>
    );
  }

  const { extra_distance_m: extra, extra_minutes: minutes, risk_reduction_pct: cut } =
    routes.tradeoff;

  return (
    <div className="a-card a-trade">
      <div className="a-trade-kicker">what it costs you</div>
      <div className="a-trade-line">
        <b>{Math.round(extra)} m</b> further
        {minutes > 0 ? `, about ${minutes} minute${minutes > 1 ? 's' : ''}` : ''}. Risk down{' '}
        <b>{cut}%</b>.
      </div>
    </div>
  );
}
