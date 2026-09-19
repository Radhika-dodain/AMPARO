// Where a user reports something: a broken street light, a lane that feels
// wrong, an incident.
//
// WHAT GOES IN HERE:
// - pick a category from a fixed list (it must match what the backend
//   accepts)
// - an optional description
// - a location - the map tap, or "use my current location"
// - submit, with the button disabled while it is sending so nobody
//   double-posts
//
// WHAT HAPPENS AFTER SUBMITTING IS THE POINT:
// The map must visibly change. The backend raises the risk of nearby streets
// the instant the report lands and tells us how many moved; this component
// shows that number, and App refetches the overlay and the route so the
// colours shift and the line moves. That sequence - report, colours change,
// route moves - is the most convincing ten seconds in the demo. It is built
// deliberately, not as a side effect.
//
// Also: it says clearly that reports are anonymous, and never asks for a name.

import { useEffect, useState } from 'react';
import { REPORT_CATEGORIES } from '../constants';
import { Tick } from './Illustrations';

export default function ReportForm({ where, onSubmit, onClose, onPickOnMap }) {
  const [category, setCategory] = useState('poor_lighting');
  const [description, setDescription] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null);

  // Escape closes it. A sheet that covers the screen and traps you is worse
  // than no sheet at all.
  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const send = async (event) => {
    event.preventDefault();
    if (!where || sending) return;

    setSending(true);
    setError(null);
    try {
      const result = await onSubmit({ ...where, category, description });
      setDone(result);
    } catch (failure) {
      setError(failure.message || 'Could not send that. Try again.');
    } finally {
      setSending(false);
    }
  };

  // ---- after it lands: show that the map actually moved ----
  if (done) {
    return (
      <div className="a-sheet-back" role="presentation" onClick={onClose}>
        <div
          className="a-sheet"
          role="dialog"
          aria-modal="true"
          aria-label="Report sent"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="a-sheet-grab" aria-hidden="true" />
          <div className="a-done">
            <Tick size={46} />
            <div>
              <div className="a-done-title">Thanks — the map just moved</div>
              <div className="a-done-note">
                <b>{done.streets_affected}</b> street
                {done.streets_affected === 1 ? '' : 's'} scored higher. Anyone routing
                through here now goes around it.
              </div>
            </div>
          </div>
          <button type="button" className="a-btn a-btn-green" onClick={onClose}>
            See the map
          </button>
        </div>
      </div>
    );
  }

  // ---- the form ----
  return (
    <div className="a-sheet-back" role="presentation" onClick={onClose}>
      <form
        className="a-sheet"
        role="dialog"
        aria-modal="true"
        aria-label="Report something"
        onClick={(event) => event.stopPropagation()}
        onSubmit={send}
      >
        <div className="a-sheet-grab" aria-hidden="true" />

        <div className="a-sheet-head">
          <h2 className="a-sheet-title">What happened here?</h2>
          <span className="a-tag">anonymous</span>
        </div>
        <p className="a-sheet-sub">No name, no account. Just this spot and what you saw.</p>

        <div className="a-where">
          {where ? (
            <span>
              Pinned at <b>{where.lat.toFixed(5)}, {where.lon.toFixed(5)}</b>
            </span>
          ) : (
            <span>No spot picked yet.</span>
          )}
          <button type="button" className="a-mini" onClick={onPickOnMap}>
            {where ? 'Move the pin' : 'Pick on the map'}
          </button>
        </div>

        <fieldset className="a-cats">
          <legend>Pick one</legend>
          <div className="a-cat-wrap">
            {REPORT_CATEGORIES.map((option) => (
              <label
                key={option.id}
                className={`a-cat ${category === option.id ? 'is-on' : ''}`}
              >
                <input
                  type="radio"
                  name="category"
                  value={option.id}
                  checked={category === option.id}
                  onChange={() => setCategory(option.id)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <label className="a-slider-title" htmlFor="report-note">
          Anything else? <span className="a-optional">optional</span>
        </label>
        <textarea
          id="report-note"
          className="a-textarea"
          rows={2}
          maxLength={500}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="No lights on the whole stretch"
        />

        {error && <p className="a-error">{error}</p>}

        <div className="a-sheet-actions">
          <button type="button" className="a-btn a-btn-quiet" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="a-btn a-btn-green" disabled={!where || sending}>
            {sending ? 'Sending…' : 'Send it'}
          </button>
        </div>
      </form>
    </div>
  );
}
