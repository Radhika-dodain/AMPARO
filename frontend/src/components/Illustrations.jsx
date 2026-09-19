// Every drawn thing in the app, in one file.
//
// These are inline SVG rather than image files on purpose: they inherit the
// palette, they stay crisp at any size, and the app ships without waiting on a
// single download. Each one is drawn as a sticker cut-out - a white outline
// around the whole silhouette, the way a paper scrap sits on a page.
//
// A NOTE ON THE ANIMATION:
// Everything here idles. Nothing darts, flashes or bounces. The map is the
// thing that matters on this screen, and a character that moves quickly will
// pull the eye off it every time. The CSS honours "reduce motion", so anyone
// who has asked their system for stillness gets it (see styles.css).
//
// Everything here is decorative, so it all carries aria-hidden. The
// information is in the text beside it, never in the drawing.

import { COLOURS } from '../constants';

// ---------------------------------------------------------------------------
// The mark
// ---------------------------------------------------------------------------
// A map pin with a leaf inside it: where you are, and the green way through.
export function Logo({ size = 44 }) {
  return (
    <svg viewBox="0 0 44 44" width={size} height={size} aria-hidden="true" className="a-logo">
      <path
        d="M22 41 C 12 30, 5 24, 5 16.5 A 12.5 12.5 0 0 1 22 5 A 12.5 12.5 0 0 1 39 16.5 C 39 24, 32 30, 22 41 Z"
        fill={COLOURS.white}
        stroke={COLOURS.deep}
        strokeWidth="2.6"
        strokeLinejoin="round"
      />
      <path d="M22 26 C 16 26, 13 22, 13 17 C 19 17, 22 20, 22 26 Z" fill={COLOURS.leafBright} />
      <path d="M22 26 C 28 26, 31 22, 31 17 C 25 17, 22 20, 22 26 Z" fill="#7BC47F" />
      <path d="M22 27 L 22 20" stroke={COLOURS.deep} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// The walker
// ---------------------------------------------------------------------------
// The person the whole app is for. Arms out, mid-stride, pleased to be walking
// home. She is the only character who ever appears at full size.
export function Walker({ width = 128 }) {
  return (
    <svg
      viewBox="0 0 128 136"
      width={width}
      height={(width * 136) / 128}
      aria-hidden="true"
      className="a-walker"
    >
      {/* one outline around the whole silhouette, drawn first so it sits behind */}
      <g stroke={COLOURS.white} strokeWidth="7" strokeLinejoin="round" fill="none">
        <path d="M 52 40 q 14 -14 28 0 l 4 26 l 12 10 l -6 12 l -12 -8 l 2 30 l 6 22 l -10 3 l -9 -22 l -8 22 l -10 -2 l 5 -24 l 1 -29 l -13 9 l -7 -12 l 13 -11 z" />
        <circle cx="66" cy="28" r="15" />
      </g>

      <path d="M 62 92 l -7 26 l 9 2 l 9 -24 z" fill="#3E6FA8" />
      <path d="M 72 92 l 8 26 l -9 2 l -8 -24 z" fill="#37649A" />
      <path d="M 53 118 q 8 -3 11 2 l 1 5 l -14 0 z" fill={COLOURS.sun} stroke={COLOURS.ink} strokeWidth="1.6" />
      <path d="M 71 120 q 8 -3 12 2 l 0 5 l -14 0 z" fill={COLOURS.sun} stroke={COLOURS.ink} strokeWidth="1.6" />
      <path d="M 54 84 l 24 0 l 2 12 l -28 0 z" fill="#3E6FA8" />
      <path d="M 52 42 q 14 -12 28 0 l 4 24 l -6 20 l -24 0 l -6 -20 z" fill="#F7D46B" />
      <path d="M 66 42 l 0 44" stroke="#E0B94A" strokeWidth="2" />
      <path d="M 54 48 l -14 12 l -7 -6" stroke="#F7D46B" strokeWidth="9" strokeLinecap="round" fill="none" />
      <path d="M 78 48 l 14 12 l 7 -6" stroke="#F7D46B" strokeWidth="9" strokeLinecap="round" fill="none" />
      <circle cx="31" cy="54" r="4.5" fill="#F0C9A8" />
      <circle cx="101" cy="54" r="4.5" fill="#F0C9A8" />
      <path d="M 80 56 q 10 2 9 12 q -1 8 -10 7 z" fill="#C58B5C" />
      <circle cx="66" cy="28" r="15" fill="#F6D5B8" />
      <path d="M 51 26 q 2 -18 15 -18 q 14 0 15 18 q -5 -8 -15 -7 q -10 1 -15 7 z" fill="#5FC0AE" />
      <path d="M 50 25 q -4 8 0 13 q 3 -6 2 -12 z" fill="#5FC0AE" />
      <path d="M 60 30 q 3 -3 6 0" stroke={COLOURS.ink} strokeWidth="1.8" fill="none" strokeLinecap="round" />
      <path d="M 70 30 q 3 -3 6 0" stroke={COLOURS.ink} strokeWidth="1.8" fill="none" strokeLinecap="round" />
      <path d="M 64 36 q 4 4 8 0" stroke={COLOURS.ink} strokeWidth="1.8" fill="none" strokeLinecap="round" />
      <circle cx="56" cy="35" r="3" fill="#F3A0A0" opacity="0.6" />
      <circle cx="79" cy="35" r="3" fill="#F3A0A0" opacity="0.6" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// The sidekick
// ---------------------------------------------------------------------------
// A penguin in a sun hat, for no reason anyone can defend. He turns up in the
// empty states, where a screen with nothing on it would otherwise feel broken.
export function Penguin({ width = 58 }) {
  return (
    <svg
      viewBox="0 0 58 70"
      width={width}
      height={(width * 70) / 58}
      aria-hidden="true"
      className="a-penguin"
    >
      <g stroke={COLOURS.white} strokeWidth="6" strokeLinejoin="round" fill="none">
        <path d="M 29 12 q 16 0 16 24 q 0 24 -16 24 q -16 0 -16 -24 q 0 -24 16 -24 z" />
      </g>
      <path d="M 29 12 q 16 0 16 24 q 0 24 -16 24 q -16 0 -16 -24 q 0 -24 16 -24 z" fill="#2E3D46" />
      <path d="M 29 22 q 9 0 9 16 q 0 16 -9 16 q -9 0 -9 -16 q 0 -16 9 -16 z" fill={COLOURS.paper} />
      <circle cx="24" cy="28" r="2" fill={COLOURS.ink} />
      <circle cx="34" cy="28" r="2" fill={COLOURS.ink} />
      <path d="M 26 33 l 6 0 l -3 5 z" fill="#F2A03D" />
      <path d="M 22 58 l -6 5 l 10 0 z" fill="#F2A03D" />
      <path d="M 36 58 l 6 5 l -10 0 z" fill="#F2A03D" />
      <path d="M 14 18 q 15 -7 30 0 q -8 3 -15 3 q -7 0 -15 -3 z" fill="#9BD6C6" />
      <path d="M 22 18 q 7 -12 14 0 z" fill="#7FC9B6" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Butterflies
// ---------------------------------------------------------------------------
export function Butterfly({ width = 22, tone = 'amber', className = '' }) {
  const wings =
    tone === 'pink' ? ['#E88CA8', '#F4AFC4'] : ['#F2A03D', '#F7C45C'];
  return (
    <svg
      viewBox="0 0 22 20"
      width={width}
      height={(width * 20) / 22}
      aria-hidden="true"
      className={`a-butterfly ${className}`}
    >
      <path d="M 11 10 q -9 -9 -10 -1 q -1 7 10 1 z" fill={wings[0]} />
      <path d="M 11 10 q 9 -9 10 -1 q 1 7 -10 1 z" fill={wings[1]} />
      <path d="M 11 8 l 0 7" stroke={COLOURS.ink} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// The sky band
// ---------------------------------------------------------------------------
// Hills, clouds, trees and a couple of birds. It stretches to whatever width
// the header is, so the shapes are drawn on a wide viewBox and allowed to
// squash rather than being cropped.
export function SkyBand({ height = 196 }) {
  return (
    <svg
      viewBox="0 0 1280 196"
      width="100%"
      height={height}
      preserveAspectRatio="none"
      aria-hidden="true"
      className="a-sky"
    >
      <g className="a-clouds" opacity="0.85">
        <ellipse cx="200" cy="44" rx="46" ry="17" fill={COLOURS.white} />
        <ellipse cx="232" cy="38" rx="30" ry="14" fill={COLOURS.white} />
        <ellipse cx="900" cy="34" rx="38" ry="14" fill={COLOURS.white} />
        <ellipse cx="928" cy="30" rx="24" ry="11" fill={COLOURS.white} />
      </g>
      <path
        d="M -20 196 C 90 130, 200 132, 300 160 C 390 186, 450 150, 560 158 C 660 166, 700 130, 810 146 C 930 164, 1010 126, 1120 148 C 1200 164, 1260 150, 1300 160 L 1300 200 L -20 200 Z"
        fill="#BEDDB4"
      />
      <path
        d="M -20 196 C 120 168, 240 176, 360 190 C 470 202, 560 176, 680 186 C 800 196, 880 172, 1000 184 C 1120 196, 1220 180, 1300 188 L 1300 210 L -20 210 Z"
        fill="#9BCB92"
      />
      <g fill={COLOURS.leafBright}>
        <path d="M 96 186 l 13 -30 l 13 30 z" />
        <path d="M 130 188 l 10 -22 l 10 22 z" />
        <path d="M 1046 184 l 13 -30 l 13 30 z" />
        <path d="M 1080 188 l 10 -22 l 10 22 z" />
        <path d="M 1114 186 l 12 -26 l 12 26 z" />
      </g>
      <g stroke="#3D6552" strokeWidth="2.5" fill="none" strokeLinecap="round" opacity="0.7">
        <path className="a-bird" d="M 640 52 q 8 -7 16 0" />
        <path className="a-bird a-bird-2" d="M 672 40 q 7 -6 14 0" />
      </g>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Small pieces
// ---------------------------------------------------------------------------

/** The paper-plane-ish flag used on the report button. */
export function ReportFlag({ size = 30 }) {
  return (
    <svg viewBox="0 0 30 30" width={size} height={size} aria-hidden="true">
      <path
        d="M 7 25 L 7 5 L 23 5 L 19 11 L 23 17 L 7 17"
        fill="#F2A03D"
        stroke="#B57420"
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** A tick in a green circle, for the moment a report lands. */
export function Tick({ size = 40 }) {
  return (
    <svg viewBox="0 0 40 40" width={size} height={size} aria-hidden="true" className="a-penguin">
      <circle cx="20" cy="20" r="18" fill="#7BC47F" />
      <path
        d="M 12 20.5 l 6 6 l 11 -13"
        fill="none"
        stroke={COLOURS.white}
        strokeWidth="3.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
