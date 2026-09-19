// Every call to the backend goes through here. No component talks to the
// server directly.
//
// Why: when an endpoint changes, or you need to add a timeout, or you want
// every failure to produce a readable message instead of a raw crash, there
// is exactly one place to do it.
//
// WHAT GOES IN HERE:
// - work out the backend address (a different port while developing, the same
//   origin once deployed)
// - getHealth()       - is the server up, did the map load, and where is the
//                       demo trip
// - getRoutes()       - send two points, the slider value and the hour;
//                       get back the fastest and safer routes with their
//                       distance and risk numbers
// - getOverlay()      - the risk colours for the whole neighbourhood
// - getPlaces()       - the police stations, hospitals and bars the risk model
//                       is built from
// - submitReport()    - send a new incident report
// - getReports()      - list reports, optionally only this session's
//
// ALSO:
// - a shared timeout, so a stalled request shows an error instead of hanging
// - retries while a sleeping free server wakes up, which takes longer than any
//   sensible single timeout
// - cancel a route request that is already in flight when the slider moves
//   again, so an older answer cannot land after a newer one and draw the
//   wrong line
// - turn server errors into sentences a person can read

// In development Vite forwards these paths to the backend, so a bare path is
// right. In production the backend serves this app itself, so a bare path is
// right again. The environment variable is only for the odd case of pointing a
// local frontend at a deployed backend.
const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');

// How long to wait for one attempt before giving up on it.
const TIMEOUT_MS = 20000;

// How long to keep retrying the very first call, in total.
//
// This number exists because of free hosting. A free server is put to sleep
// after a quiet spell, and the first visitor's request is what wakes it -
// which takes the better part of a minute, during which connections are simply
// dropped. The app used to treat that as "the backend is down", show an error,
// and sit there forever until somebody thought to refresh. On a demo day, that
// somebody is a judge, and they will not think to refresh.
const WAKE_BUDGET_MS = 90000;

/** Thrown for anything the user might need to read. `.message` is safe to show. */
export class ApiError extends Error {
  constructor(message, { status = 0, cause = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.cause = cause;
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Turn whatever the server said into one sentence a person can read.
 *
 * FastAPI reports a failed check as a list of objects, which is precise and
 * completely unreadable. The useful half is almost always the message on the
 * first one.
 */
function readableError(status, body) {
  const detail = body && body.detail;

  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    const message = (first && first.msg) || '';
    // Pydantic prefixes its own messages; the prefix means nothing to a user.
    return message.replace(/^Value error,\s*/i, '') || 'That request was not valid.';
  }
  if (typeof detail === 'string' && detail) return detail;

  if (status === 404) return 'No walkable route between those two points.';
  if (status === 503) return 'The map is still loading. Give it a moment.';
  if (status >= 500) return 'The server had a problem. Try that again.';
  return 'Something went wrong talking to the server.';
}

/** One attempt. Throws ApiError for anything retryable, AbortError if cancelled. */
async function attempt(path, { method = 'GET', body, signal } = {}) {
  // Two things can cancel a request: our own timeout, and the caller changing
  // their mind. They have to be told apart - a timeout is worth retrying, a
  // caller who navigated away is not - so the timeout raises a flag on its way
  // past, because the browser reports both as the same AbortError.
  const timer = new AbortController();
  let timedOut = false;
  const timeout = setTimeout(() => {
    timedOut = true;
    timer.abort();
  }, TIMEOUT_MS);

  if (signal) {
    if (signal.aborted) timer.abort();
    else signal.addEventListener('abort', () => timer.abort(), { once: true });
  }

  let response;
  try {
    response = await fetch(BASE + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: timer.signal,
    });
  } catch (error) {
    clearTimeout(timeout);
    if (error.name === 'AbortError' && !timedOut) throw error; // caller's doing
    throw new ApiError('Could not reach the server.', { status: 0, cause: error });
  }
  clearTimeout(timeout);

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiError(readableError(response.status, payload), {
      status: response.status,
    });
  }
  return payload;
}

/** Is this worth trying again, or is it our own fault? */
function worthRetrying(error) {
  if (!(error instanceof ApiError)) return false;
  // 0 means we never got a reply at all. 502/503/504 are what a host returns
  // while it is still bringing the app up. A 400 or a 404 is our own mistake
  // and will fail identically forever.
  return error.status === 0 || error.status === 502 || error.status === 503 || error.status === 504;
}

/**
 * A request, retried while the server might still be waking.
 *
 * `wakeBudgetMs` is how long to persist. `onWaking` is called before each
 * retry so the interface can say what is happening rather than looking frozen.
 */
async function request(path, { wakeBudgetMs = 0, onWaking, ...options } = {}) {
  const giveUpAt = Date.now() + wakeBudgetMs;
  let tries = 0;

  for (;;) {
    try {
      return await attempt(path, options);
    } catch (error) {
      tries += 1;
      if (!worthRetrying(error) || Date.now() >= giveUpAt) {
        // Out of patience. Say something a person can act on.
        if (error instanceof ApiError && error.status === 0) {
          error.message = tries > 1
            ? 'The server is taking too long to wake up. Try again in a moment.'
            : 'Could not reach the server. Is the backend running?';
        }
        throw error;
      }
      if (onWaking) onWaking(tries);
      // Back off, but not for long: 1s, 2s, 4s, then every 6s.
      await sleep(Math.min(1000 * 2 ** (tries - 1), 6000));
    }
  }
}

// ---------------------------------------------------------------------------
// The endpoints
// ---------------------------------------------------------------------------

/**
 * Is the server up, did the map load, and what should the app be set to?
 *
 * Called once at startup. It carries the things the frontend would otherwise
 * have to hardcode and then keep in step by hand: the area name and bounds,
 * the emergency number, the report categories, and the demo trip.
 */
export function getHealth(signal, onWaking) {
  // The one call that persists through a cold start. Everything else can fail
  // and be retried by the user; without this one there is no map at all, so it
  // is worth waiting out a sleeping server for.
  return request('/health', { signal, wakeBudgetMs: WAKE_BUDGET_MS, onWaking });
}

/** Two points in, two routes out, with the numbers that describe them. */
export function getRoutes({ origin, dest, k, hour }, signal) {
  return request('/route', {
    method: 'POST',
    signal,
    body: {
      origin_lat: origin.lat,
      origin_lon: origin.lon,
      dest_lat: dest.lat,
      dest_lon: dest.lon,
      // The slider runs 0-100 for the UI; the backend wants 0-1.
      k: k / 100,
      hour,
    },
  });
}

/** Every street with its risk band, for shading the map. */
export function getOverlay({ hour, riskyOnly = false }, signal) {
  const query = new URLSearchParams({ hour: String(hour) });
  if (riskyOnly) query.set('risky_only', 'true');
  // Also worth waiting out a cold start: without it the map has no colour.
  return request(`/safety/overlay?${query}`, { signal, wakeBudgetMs: WAKE_BUDGET_MS });
}

/** The places the risk model is built from. Fetched once and kept. */
export function getPlaces(signal) {
  return request('/safety/places', { signal, wakeBudgetMs: WAKE_BUDGET_MS });
}

/**
 * Send a report.
 *
 * The answer is worth reading: it says how many streets moved and what the new
 * overlay version is, which is what lets the app refetch and visibly show that
 * something happened rather than just saying "saved".
 */
export function submitReport({ lat, lon, category, description, sessionId }, signal) {
  return request('/reports', {
    method: 'POST',
    signal,
    body: {
      lat,
      lon,
      category,
      description: description || '',
      session_id: sessionId || '',
    },
  });
}

/** Reports, newest first. Pass a session id for "mine only". */
export function getReports({ sessionId, limit = 50 } = {}, signal) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (sessionId) query.set('session_id', sessionId);
  return request(`/reports?${query}`, { signal });
}
