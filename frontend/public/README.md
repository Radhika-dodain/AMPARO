# public/

Files served as-is, untouched by the build.

- `favicon.svg` — the tab icon

Nothing else lives here yet, and two things people expect to find are
deliberately absent:

- **No alarm.mp3.** The panic button's siren is generated in the browser with
  a couple of oscillators, so there is no audio file to download, fail to
  load, or add to the repo. See `src/components/PanicButton.jsx`.
- **No map images.** Every illustration in the app is inline SVG in
  `src/components/Illustrations.jsx`, so it inherits the palette and stays
  sharp at any size.
