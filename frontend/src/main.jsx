// The first file the browser runs.
//
// Tiny on purpose: pull in the stylesheets, find the empty div in
// index.html, and mount the App into it. Nothing else belongs here.
//
// Leaflet's own stylesheet has to come BEFORE ours. It ships defaults for the
// zoom buttons, popups and attribution, and ours override several of them -
// load it second and it wins, and the map furniture goes back to looking like
// stock Leaflet.

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import 'leaflet/dist/leaflet.css';
import './styles.css';

import App from './App';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
