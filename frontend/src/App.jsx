// The shell that holds everything and owns the shared state.
//
// Layout: the map fills the screen, and a panel sits over it - on the side on
// a laptop, sliding up from the bottom on a phone. The panic button floats
// above everything else, always reachable.
//
// WHAT THIS FILE KEEPS TRACK OF (everything else just receives it):
// - where the user is starting from and going to
// - the safety slider value
// - the time of day (day / evening / night)
// - the two routes that came back, and which one is currently highlighted
// - which map layers are switched on
// - whether the report form is open
// - loading and error states
//
// WHAT IT DOES:
// - reads settings off /health at startup, so the area, the emergency number
//   and the demo trip all come from the backend and cannot drift out of step
// - fetches the risk overlay, and refetches it when the hour changes
// - asks for new routes whenever the start, end, slider or time changes
//   (the waiting-for-a-pause lives in useRoutes)
// - refetches the overlay AND the route after a report is submitted, so the
//   map visibly changes - that visible change is the demo moment
// - shows a friendly first-time hint: "tap the map to set where you are"

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { getHealth, getOverlay, getPlaces, submitReport } from './api';
import {
  EMERGENCY_FALLBACK,
  SLIDER,
  TIME_PRESETS,
  currentPreset,
} from './constants';
import { useGeolocation } from './hooks/useGeolocation';
import { useRoutes } from './hooks/useRoutes';
import { useSession } from './hooks/useSession';

import HistoryList from './components/HistoryList';
import { Butterfly, Logo, SkyBand, Walker, Penguin, ReportFlag } from './components/Illustrations';
import Legend from './components/Legend';
import MapControls from './components/MapControls';
import MapView from './components/MapView';
import PanicButton from './components/PanicButton';
import ReportForm from './components/ReportForm';
import RoutePlanner from './components/RoutePlanner';
import RouteStats from './components/RouteStats';
import SafetySlider from './components/SafetySlider';
import TimeOfDayToggle from './components/TimeOfDayToggle';

const hourFor = (preset) => TIME_PRESETS.find((p) => p.id === preset).hour;

export default function App() {
  // ---- what the backend tells us about itself ----
  const [health, setHealth] = useState(null);
  const [bootError, setBootError] = useState(null);
  const [waking, setWaking] = useState(0); // retry count while the server wakes
  const [bootAttempt, setBootAttempt] = useState(0); // bumped by the Retry button

  // ---- the trip ----
  const [origin, setOrigin] = useState(null);
  const [dest, setDest] = useState(null);
  const [k, setK] = useState(SLIDER.start);
  const [preset, setPreset] = useState(currentPreset);
  const [selected, setSelected] = useState('safer');

  // ---- the map ----
  const [overlay, setOverlay] = useState(null);
  const [places, setPlaces] = useState(null);
  const [layers, setLayers] = useState({ risk: true, places: false, quiet: false });

  // ---- reporting ----
  const [reportOpen, setReportOpen] = useState(false);
  const [reportAt, setReportAt] = useState(null);
  const [pickingReport, setPickingReport] = useState(false);
  const [myReports, setMyReports] = useState(0); // bumped to refresh the list

  const [panelOpen, setPanelOpen] = useState(false); // phone bottom sheet
  const [showHistory, setShowHistory] = useState(false);

  const hour = hourFor(preset);
  const { sessionId, resetSession } = useSession();
  const geo = useGeolocation();
  const { routes, loading, error, refresh } = useRoutes({ origin, dest, k, hour });

  const panelRef = useRef(null);

  // When the sheet is collapsed on a phone, most of it is clipped out of
  // sight. Anything down there can still be reached by keyboard, and a browser
  // that moves focus into a clipped area scrolls to reach it - which silently
  // slides the sheet's contents up and leaves the peeking strip showing
  // whatever happened to land there. So: focus inside the sheet opens it, and
  // collapsing it always returns to the top.
  useEffect(() => {
    if (!panelOpen && panelRef.current) panelRef.current.scrollTop = 0;
  }, [panelOpen]);

  // ---- startup: settings, then the overlay and the places ----
  useEffect(() => {
    const controller = new AbortController();

    getHealth(controller.signal, setWaking)
      .then((result) => {
        setHealth(result);
        setWaking(0);
      })
      .catch((failure) => {
        if (failure.name !== 'AbortError') setBootError(failure.message);
      });

    getPlaces(controller.signal)
      .then(setPlaces)
      .catch(() => setPlaces(null)); // a missing places layer is survivable

    return () => controller.abort();
  }, [bootAttempt]);

  // ---- the overlay, refetched whenever the hour changes ----
  const loadOverlay = useCallback(
    (signal) =>
      getOverlay({ hour }, signal)
        .then(setOverlay)
        .catch(() => {
          /* the map still works without shading */
        }),
    [hour],
  );

  useEffect(() => {
    const controller = new AbortController();
    loadOverlay(controller.signal);
    return () => controller.abort();
  }, [loadOverlay]);

  // ---- tapping the map ----
  const onPick = useCallback(
    (point) => {
      // While the report sheet is asking for a spot, a tap means "here".
      if (pickingReport) {
        setReportAt(point);
        setPickingReport(false);
        setReportOpen(true);
        return;
      }
      // Otherwise: first tap sets the start, second the finish, third starts over.
      if (!origin) setOrigin(point);
      else if (!dest) setDest(point);
      else {
        setOrigin(point);
        setDest(null);
      }
      // Deliberately NOT opening the sheet here. On a phone the sheet covers
      // the map, and the map is the thing they just asked a question about -
      // the peeking strip already shows the answer.
    },
    [origin, dest, pickingReport],
  );

  const useDemoTrip = useCallback(() => {
    if (!health) return;
    const [oLat, oLon] = health.demo_route.origin;
    const [dLat, dLon] = health.demo_route.destination;
    setOrigin({ lat: oLat, lon: oLon });
    setDest({ lat: dLat, lon: dLon });
    setSelected('safer');
  }, [health]);

  const locate = useCallback(async () => {
    const found = await geo.locate();
    if (found) setOrigin({ lat: found.lat, lon: found.lon });
  }, [geo]);

  // ---- the moment that sells the whole thing ----
  const sendReport = useCallback(
    async (report) => {
      const result = await submitReport({ ...report, sessionId });
      // Both of these matter. The overlay refetch recolours the streets, the
      // route refresh makes the line move. Either one alone is half the moment.
      await loadOverlay();
      refresh();
      setMyReports((n) => n + 1);
      return result;
    },
    [sessionId, loadOverlay, refresh],
  );

  const emergency = health?.emergency_number || EMERGENCY_FALLBACK;
  const bands = overlay?.counts;

  // What the header says about the server, in that order of priority.
  //
  // The waking message matters more than it looks. Free hosting sleeps when
  // nobody has visited for a while, and the first person through the door
  // waits the better part of a minute. Telling them that is the difference
  // between "it is coming" and "this is broken" - and the person reading it
  // might be a judge who will not think to refresh.
  const headerNote = useMemo(() => {
    if (bootError) return bootError;
    if (waking > 0) return 'Waking the server up — free hosting sleeps when idle…';
    if (!health) return 'Loading…';
    return `${health.edges.toLocaleString()} streets scored`;
  }, [health, bootError, waking]);

  return (
    <div className="a-app">
      {/* ============ illustrated header ============ */}
      <header className="a-header">
        <div className="a-sky-wrap" aria-hidden="true">
          <SkyBand height={168} />
        </div>

        <div className="a-header-row">
          <Logo size={42} />
          <div className="a-wordmark">
            <div className="a-name">Amparo</div>
            <div className="a-tagline">map your own safety</div>
          </div>

          <div className="a-header-right">
            <div className="a-place-pill">
              <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                <path
                  d="M8 15 C 4 10.5, 1.8 8.4, 1.8 6 A 6.2 6.2 0 0 1 14.2 6 C 14.2 8.4, 12 10.5, 8 15 Z"
                  fill="none"
                  stroke="#276B42"
                  strokeWidth="1.8"
                />
                <circle cx="8" cy="6" r="2.1" fill="#4E9E63" />
              </svg>
              <span>{health?.area || 'Loading…'}</span>
            </div>
            <TimeOfDayToggle value={preset} onChange={setPreset} compact />
            <button
              type="button"
              className="a-mini"
              onClick={() => setShowHistory((open) => !open)}
              aria-expanded={showHistory}
            >
              My reports
            </button>
          </div>
        </div>

        {/* the cast, standing on the ridge */}
        <div className="a-cast" aria-hidden="true">
          <Walker width={104} />
          <Penguin width={46} />
        </div>
        <Butterfly className="a-fly-1" width={20} />
        <Butterfly className="a-fly-2" width={17} tone="pink" />

        <div className={`a-header-note ${bootError ? 'is-bad' : ''}`}>
          {headerNote}
          {bootError && (
            <button
              type="button"
              onClick={() => {
                // Cleared here rather than inside the effect: clearing state on
                // the way into an effect costs an extra render every time it
                // runs, for something only this button ever needs.
                setBootError(null);
                setBootAttempt((n) => n + 1);
              }}
            >
              Try again
            </button>
          )}
        </div>
      </header>

      {/* ============ the map ============ */}
      <main className="a-main">
        <div className="a-mapcard">
          <MapView
            bbox={health?.bbox}
            origin={origin}
            dest={dest}
            routes={routes}
            overlay={overlay}
            places={places}
            layers={layers}
            selected={selected}
            onSelect={setSelected}
            onPick={onPick}
          />

          <MapControls layers={layers} onChange={setLayers} bands={bands} />

          {pickingReport && (
            <div className="a-picking">Tap the spot you want to report</div>
          )}

          <RouteStats routes={routes} selected={selected} />

          <PanicButton number={emergency} here={origin} />

          <p className="a-proto">
            Real streets from OpenStreetMap. Risk scored by Amparo over{' '}
            {health ? health.edges.toLocaleString() : '—'} walkable segments.
          </p>
        </div>

        {/* ============ side panel / bottom sheet ============ */}
        <aside
          ref={panelRef}
          className={`a-panel ${panelOpen ? 'is-open' : ''}`}
          onFocusCapture={(event) => {
            // The grab bar is the one control that must not force it open -
            // that is the button you press to close it.
            if (!event.target.classList.contains('a-panel-grab')) setPanelOpen(true);
          }}
        >
          <button
            type="button"
            className="a-panel-grab"
            onClick={() => setPanelOpen((open) => !open)}
            aria-expanded={panelOpen}
            aria-label={panelOpen ? 'Hide the panel' : 'Show the panel'}
          />

          {showHistory ? (
            <div className="a-card">
              <h2 className="a-sheet-title">My reports</h2>
              <HistoryList
                sessionId={sessionId}
                refreshKey={myReports}
                onFocus={() => setShowHistory(false)}
                onForget={resetSession}
              />
            </div>
          ) : (
            <>
              <RoutePlanner
                origin={origin}
                dest={dest}
                routes={routes}
                loading={loading}
                error={error}
                selected={selected}
                onSelect={setSelected}
                onSwap={() => {
                  setOrigin(dest);
                  setDest(origin);
                }}
                onClear={() => {
                  setOrigin(null);
                  setDest(null);
                }}
                onClearOne={(which) => (which === 'origin' ? setOrigin(null) : setDest(null))}
                onDemo={useDemoTrip}
                onLocate={locate}
                locating={geo.loading}
                locateError={geo.error}
              />

              <SafetySlider value={k} onChange={setK} routes={routes} />

              <TimeOfDayToggle value={preset} onChange={setPreset} />

              <button
                type="button"
                className="a-report-btn"
                onClick={() => {
                  setPickingReport(true);
                  setPanelOpen(false);
                }}
              >
                <ReportFlag size={28} />
                <span>
                  <b>Something felt wrong here?</b>
                  <em>Tell us — the map changes for everyone</em>
                </span>
              </button>

              <Legend />
            </>
          )}
        </aside>
      </main>

      {reportOpen && (
        <ReportForm
          where={reportAt}
          onSubmit={sendReport}
          onClose={() => {
            setReportOpen(false);
            setReportAt(null);
          }}
          onPickOnMap={() => {
            setReportOpen(false);
            setPickingReport(true);
          }}
        />
      )}
    </div>
  );
}
