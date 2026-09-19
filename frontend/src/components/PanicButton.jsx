// The emergency button. Entirely self-contained - it never needs the server,
// so it still works if the backend is down.
//
// WHAT GOES IN HERE:
// - a floating red button, always visible, never scrolled away
// - tapping it opens a panel with: call the emergency number, copy a link to
//   your current location to send someone, and a loud looping alarm
// - a confirm step before dialling, so a pocket tap does not call emergency
//   services
//
// THE TRAP THAT KILLS THIS LIVE:
// A "tap to call" link does nothing on a laptop. If you demo on a laptop, the
// panic button appears dead. So the number is ALSO printed in large type you
// can read out, with a copy button beside it - the panel does something
// visible on every device. Test it on a laptop before the pitch, not on it.
//
// The alarm is generated rather than loaded from a file, so there is no audio
// download to fail and nothing to add to the repo. It is a harsh two-tone
// warble, on purpose.

import { useCallback, useEffect, useRef, useState } from 'react';

function useAlarm() {
  const context = useRef(null);
  const nodes = useRef(null);
  const [playing, setPlaying] = useState(false);

  const stop = useCallback(() => {
    if (nodes.current) {
      nodes.current.gain.gain.value = 0;
      nodes.current.oscillator.stop();
      nodes.current = null;
    }
    setPlaying(false);
  }, []);

  const start = useCallback(() => {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    if (!context.current) context.current = new Ctx();
    context.current.resume();

    const oscillator = context.current.createOscillator();
    const gain = context.current.createGain();
    // Two-tone warble: the sound of something that wants attention.
    const sweep = context.current.createOscillator();
    const sweepDepth = context.current.createGain();

    oscillator.type = 'square';
    oscillator.frequency.value = 760;
    sweep.frequency.value = 4;
    sweepDepth.gain.value = 260;
    sweep.connect(sweepDepth).connect(oscillator.frequency);

    gain.gain.value = 0.16;
    oscillator.connect(gain).connect(context.current.destination);
    oscillator.start();
    sweep.start();

    nodes.current = { oscillator, gain };
    setPlaying(true);
  }, []);

  // Never leave a siren running because a component went away.
  useEffect(() => () => stop(), [stop]);

  return { playing, start, stop };
}

export default function PanicButton({ number, here }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const alarm = useAlarm();

  const shareLink = here
    ? `https://www.google.com/maps/search/?api=1&query=${here.lat.toFixed(5)},${here.lon.toFixed(5)}`
    : null;

  const copy = async () => {
    if (!shareLink) return;
    try {
      await navigator.clipboard.writeText(`I am here: ${shareLink}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    } catch {
      setCopied(false);
    }
  };

  const close = useCallback(() => {
    alarm.stop();
    setOpen(false);
  }, [alarm]);

  // Escape closes it, and stops the siren on the way out. Anything that covers
  // the whole screen has to be dismissable from the keyboard.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') close();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, close]);

  return (
    <>
      <button
        type="button"
        className="a-sos"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-label={`Emergency options. Emergency number ${number}`}
      >
        SOS
        <span>{number}</span>
      </button>

      {open && (
        <div className="a-sheet-back" role="presentation" onClick={close}>
          <div
            className="a-sheet a-sos-sheet"
            role="dialog"
            aria-modal="true"
            aria-label="Emergency"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="a-sheet-grab" aria-hidden="true" />

            <h2 className="a-sheet-title">Need help now?</h2>

            {/* Printed large, because a tel: link does nothing on a laptop and
                a number you can read aloud always works. */}
            <div className="a-sos-number">
              <span>{number}</span>
              <a className="a-btn a-btn-red" href={`tel:${number}`}>
                Call
              </a>
            </div>

            <div className="a-sos-actions">
              <button type="button" className="a-btn a-btn-ghost" onClick={copy} disabled={!shareLink}>
                {copied ? 'Copied — now paste it to someone' : 'Copy my location'}
              </button>
              <button
                type="button"
                className={`a-btn ${alarm.playing ? 'a-btn-red' : 'a-btn-ghost'}`}
                onClick={alarm.playing ? alarm.stop : alarm.start}
              >
                {alarm.playing ? 'Stop the alarm' : 'Sound an alarm'}
              </button>
            </div>

            {!shareLink && (
              <p className="a-warn">
                Set a start point first, and there will be a location to send.
              </p>
            )}

            <button type="button" className="a-btn a-btn-quiet" onClick={close}>
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
