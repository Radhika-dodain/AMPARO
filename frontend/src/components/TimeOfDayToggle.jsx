// Day / evening / night switch.
//
// Street lighting means nothing at noon and nightlife means nothing at 3pm.
// Flipping this changes the risk scores, so the colours cool down and the
// routes actually move - which is a genuinely good thing to demo.
//
// WHAT GOES IN HERE:
// - three buttons: day, evening, night
// - default to whatever time it actually is right now
// - changing it refetches both the overlay and the routes
// - a one-line explanation of what changed, so the user understands why the
//   map just looked different
//
// WORTH KNOWING BEFORE YOU DEMO IT:
// In this area, switching to Day makes the two routes collapse into one. That
// is not a failure - at noon the quickest way really is the calmest way, and
// the app says so. It is a better moment than it sounds: it shows the model
// answering honestly instead of always manufacturing a detour.

import { TIME_PRESETS } from '../constants';

const BLURB = {
  day: 'At noon, lighting and nightlife count for nothing. Only the street itself matters.',
  evening: 'Dusk. Lighting and bars start to weigh in, at about half strength.',
  night: 'After dark, lighting and nightlife count for everything they are worth.',
};

export default function TimeOfDayToggle({ value, onChange, compact = false }) {
  return (
    <div className={`a-tod ${compact ? 'is-compact' : ''}`}>
      <div className="a-chips" role="group" aria-label="Time of day">
        {TIME_PRESETS.map((preset) => {
          const on = preset.id === value;
          return (
            <button
              key={preset.id}
              type="button"
              className={`a-chip ${on ? 'is-on' : ''}`}
              aria-pressed={on}
              onClick={() => onChange(preset.id)}
            >
              {preset.label}
            </button>
          );
        })}
      </div>
      {!compact && <p className="a-tod-blurb">{BLURB[value]}</p>}
    </div>
  );
}
