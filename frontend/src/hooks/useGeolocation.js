// Asks the browser where the user is.
//
// WHAT GOES IN HERE:
// - request the location only when the user actually taps a button, never on
//   page load - a permission popup the instant the app opens is the fastest
//   way to get denied
// - handle the three ways it fails: permission refused, unavailable, timed out
// - hand back the position, whether it is still working, and any error
//
// THE TESTING TRAP:
// Browsers only give out location on a secure connection. Opening the app on
// your phone via your laptop's local network address is not one, so this
// silently refuses - and it is easy to think the code is broken. Test on the
// deployed URL, or use the demo preset points instead.

import { useCallback, useState } from 'react';

// Spelled out, because the browser reports these as bare numbers and a user
// staring at "error 1" learns nothing.
const MESSAGES = {
  1: 'Location permission was declined. You can tap the map instead.',
  2: 'Your location is not available right now. Tap the map instead.',
  3: 'Finding you took too long. Tap the map instead.',
};

const INSECURE =
  'Your browser only shares location over a secure connection. Open the deployed link, or tap the map to set your start.';

export function useGeolocation() {
  const [position, setPosition] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const locate = useCallback(() => {
    setError(null);

    if (!('geolocation' in navigator)) {
      setError('This browser cannot share your location.');
      return Promise.resolve(null);
    }

    // Catch the local-network case before the browser does, so the message
    // explains the real problem instead of just saying "denied".
    if (!window.isSecureContext) {
      setError(INSECURE);
      return Promise.resolve(null);
    }

    setLoading(true);
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (result) => {
          const found = {
            lat: result.coords.latitude,
            lon: result.coords.longitude,
            accuracy: result.coords.accuracy,
          };
          setPosition(found);
          setLoading(false);
          resolve(found);
        },
        (failure) => {
          setError(MESSAGES[failure.code] || 'Could not find you. Tap the map instead.');
          setLoading(false);
          resolve(null);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 },
      );
    });
  }, []);

  return { position, loading, error, locate };
}
