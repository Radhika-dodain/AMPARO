// The reports this user has submitted.
//
// WHAT GOES IN HERE:
// - read the anonymous session id (see hooks/useSession.js)
// - ask the backend for this session's reports
// - list them newest first, with time, category and a rough location
// - tapping one centres the map there
// - trip history is kept in the browser only, never sent to the server -
//   where somebody walks is the most sensitive data this app touches and
//   there is no reason for it to leave their phone
// - a "clear my history" button, and it must actually clear it
//
// A friendly empty state, because on first open this is always empty.
//
// ON "CLEAR MY HISTORY": it forgets the anonymous id, so this browser stops
// being able to claim those reports. The reports themselves stay on the map -
// they belong to the neighbourhood now, and the point of the whole feature is
// that they keep protecting people. The wording says so plainly rather than
// implying a delete we do not do.

import { useEffect, useState } from 'react';
import { getReports } from '../api';
import { REPORT_CATEGORIES } from '../constants';
import { Penguin } from './Illustrations';

const NAMES = Object.fromEntries(REPORT_CATEGORIES.map((c) => [c.id, c.label]));

export default function HistoryList({ sessionId, onFocus, onForget, refreshKey }) {
  // One piece of state, not three. Tracking rows, loading and error separately
  // meant flipping a flag on the way into the effect, which starts a render
  // just to say "about to fetch" - and leaves a window where the list is both
  // loading and holding the previous session's rows.
  const [state, setState] = useState({ status: 'loading', rows: [], error: null });

  useEffect(() => {
    const controller = new AbortController();
    let live = true;

    getReports({ sessionId }, controller.signal)
      .then((rows) => {
        if (live) setState({ status: 'ready', rows, error: null });
      })
      .catch((failure) => {
        if (live && failure.name !== 'AbortError') {
          setState({ status: 'error', rows: [], error: failure.message });
        }
      });

    return () => {
      live = false;
      controller.abort();
    };
  }, [sessionId, refreshKey]);

  const { status, rows, error } = state;
  const loading = status === 'loading';

  if (loading) return <p className="a-quiet">Looking…</p>;
  if (error) return <p className="a-error">{error}</p>;

  if (rows.length === 0) {
    return (
      <div className="a-empty a-empty-plain">
        <Penguin width={46} />
        <div>
          <div className="a-empty-title">Nothing from you yet</div>
          <div className="a-empty-note">
            Anything you report shows up here, and on everyone&rsquo;s map.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="a-history">
      <ul className="a-history-list">
        {rows.map((row) => (
          <li key={row.id}>
            <button type="button" onClick={() => onFocus({ lat: row.lat, lon: row.lon })}>
              <span className="a-history-cat">{NAMES[row.category] || row.category}</span>
              <span className="a-history-when">{row.created_at_local}</span>
              {row.description && <span className="a-history-note">{row.description}</span>}
            </button>
          </li>
        ))}
      </ul>

      <button type="button" className="a-mini" onClick={onForget}>
        Forget me on this device
      </button>
      <p className="a-fineprint">
        That clears the anonymous id this browser uses. The reports stay on the map —
        they are helping other people now.
      </p>
    </div>
  );
}
