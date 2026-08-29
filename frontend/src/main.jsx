import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import { registerServiceWorker } from './services/pwa.js';
import { applyTheme, isDarkTheme } from './services/preferences.js';
import './styles.css';
import './styles-app.css';
import './styles-landing.css';

// Applied before the first paint so a dark-mode visitor never sees a light flash.
applyTheme(isDarkTheme());

createRoot(document.getElementById('root')).render(<App />);

registerServiceWorker();
