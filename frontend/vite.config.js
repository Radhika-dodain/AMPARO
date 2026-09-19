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

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    // Job 1: hand API calls to the backend so the app can use bare paths.
    proxy: Object.fromEntries(
      API_PATHS.map((path) => [
        path,
        { target: 'http://127.0.0.1:8000', changeOrigin: true },
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
