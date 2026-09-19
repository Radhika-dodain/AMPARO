// Owns the fetching of routes, so App.jsx does not fill up with request
// plumbing.
//
// WHAT GOES IN HERE:
// - watch the start point, end point, slider value and time of day
// - when any of them changes, ask the backend for new routes
// - wait for a pause before firing, so dragging the slider does not send a
//   request per pixel
// - throw away an older answer if a newer request has already gone out,
//   otherwise a slow reply can land last and draw the wrong route
// - hand back: the routes, whether it is loading, and any error
// - a manual refresh, for after a report is submitted

import { useCallback, useEffect, useRef, useState } from 'react';
import { getRoutes } from '../api';

// Long enough that a slider drag is one request, short enough that it still
// feels like the map is answering you.
const SETTLE_MS = 260;

export function useRoutes({ origin, dest, k, hour }) {
  const [routes, setRoutes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // The request currently in the air, so a new one can cancel it.
  const inFlight = useRef(null);
  // Bumped to force a refetch with unchanged inputs (after a report lands).
  const [nonce, setNonce] = useState(0);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    // No trip yet: nothing to ask for. Note we do NOT clear the stored routes
    // here - clearing state from inside an effect kicks off a second render
    // for no reason. What the caller sees is worked out at the bottom instead.
    if (!origin || !dest) return undefined;

    let cancelled = false;
    const timer = setTimeout(async () => {
      // Cancel whatever is still in the air. Without this a slow earlier
      // answer can arrive after a newer one and draw a route the slider has
      // already moved away from.
      if (inFlight.current) inFlight.current.abort();
      const controller = new AbortController();
      inFlight.current = controller;

      setLoading(true);
      setError(null);
      try {
        const result = await getRoutes({ origin, dest, k, hour }, controller.signal);
        if (!cancelled) setRoutes(result);
      } catch (failure) {
        // A cancelled request is not an error - we cancelled it on purpose.
        if (failure.name === 'AbortError' || cancelled) return;
        setError(failure.message || 'Could not work out a route.');
        setRoutes(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, SETTLE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [origin, dest, k, hour, nonce]);

  // Derived, not stored. With no start or finish there is no route to show,
  // whatever happens to be left in state from the last one.
  const ready = Boolean(origin && dest);

  return {
    routes: ready ? routes : null,
    loading: ready && loading,
    error: ready ? error : null,
    refresh,
  };
}
