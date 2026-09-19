// Gives this browser an anonymous id, so "my reports" can work without
// anybody logging in.
//
// WHAT GOES IN HERE:
// - on first visit, make up a random id and remember it in the browser
// - hand the same id back on every later visit
// - a way to wipe it, which effectively makes the user a new anonymous person
//
// No accounts, no email, no password. A random string is enough for
// everything this app needs, and it means there is no personal data to lose.

import { useCallback, useState } from 'react';

const KEY = 'amparo.session';

function makeId() {
  // crypto.randomUUID is not there in older browsers or on an insecure
  // connection, which is exactly the phone-over-local-network case we test in.
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  return 'sess-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

// Private browsing and blocked site data make storage throw rather than return
// nothing, so every touch of it is wrapped. A session id is a convenience: if
// it cannot be kept, the app still works, the user just sees no history.
function read() {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function write(value) {
  try {
    window.localStorage.setItem(KEY, value);
  } catch {
    /* nothing to do - the app works without it */
  }
}

export function useSession() {
  const [sessionId, setSessionId] = useState(() => {
    const existing = read();
    if (existing) return existing;
    const fresh = makeId();
    write(fresh);
    return fresh;
  });

  /** Become a different anonymous person. The old reports stay on the map. */
  const resetSession = useCallback(() => {
    const fresh = makeId();
    write(fresh);
    setSessionId(fresh);
    return fresh;
  }, []);

  return { sessionId, resetSession };
}
