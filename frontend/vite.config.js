// Build settings for the frontend.
//
// Two jobs:
//
// 1. While developing, the frontend runs on its own port and the backend on
//    another. Forward anything that looks like an API call over to the
//    backend, so the code can just say "/route" and not care which port it
//    is on.
//
// 2. When building for real, put the finished files straight into the
//    backend's folder, so one server hands out both the app and the API.
//    One URL, nothing to configure, nothing to go wrong on demo day.

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Every path the backend owns. Anything not on this list is the app itself.
const API_PATHS = ['/health', '/route', '/safety', '/reports'];

// NOTE ON A `public/` FOLDER, if you ever add one back:
// everything inside it is copied to the live site as-is, at the top level. A
// developer note left in there is published at yoursite.com/that-file, which
// happened once already with a README. Only real assets belong there - a
// favicon, an og-image. Developer notes go in the code.

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    // Job 1: hand API calls to the backend so the app can use bare paths.
    proxy: Object.fromEntries(
      API_PATHS.map((path) => [
        path,
        {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,

          // Answer 503 when the backend is not up yet, instead of the 500 the
          // proxy would otherwise invent.
          //
          // This is not pedantry. 503 means "there is a service here and it is
          // not ready", which is exactly what a sleeping free server sends
          // while it wakes - so the app's retry-and-wait behaviour kicks in
          // locally too. Reported as 500 the app gives up immediately, and the
          // one code path you most want to rehearse before a demo is the one
          // you cannot reproduce on your own machine.
          configure: (proxy) => {
            proxy.on('error', (_error, _request, response) => {
              if (response && !response.headersSent && response.writeHead) {
                response.writeHead(503, { 'Content-Type': 'application/json' });
                response.end(
                  JSON.stringify({ detail: 'Backend is not running yet.' }),
                );
              }
            });
          },
        },
      ]),
    ),
  },

  build: {
    // Job 2: build straight into the folder the backend serves from.
    outDir: '../backend/frontend_dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 900, // Leaflet is chunky and that is fine
  },
});
