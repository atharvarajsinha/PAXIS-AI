/**
 * Install-prompt plumbing.
 *
 * `beforeinstallprompt` fires once, early, and usually before React has
 * mounted, so the listener is registered at module load and the event is
 * stashed here. Components subscribe instead of listening themselves.
 */

let deferredPrompt = null;
let installed = false;
const listeners = new Set();

const notify = () => listeners.forEach((listener) => listener());

export function isStandalone() {
  try {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      window.matchMedia('(display-mode: window-controls-overlay)').matches ||
      window.navigator.standalone === true
    );
  } catch {
    return false;
  }
}

/** iOS has no install prompt API - Safari needs Share > Add to Home Screen. */
export function isIosSafari() {
  const ua = window.navigator.userAgent || '';
  const isIos = /iPad|iPhone|iPod/.test(ua) || (ua.includes('Macintosh') && 'ontouchend' in document);
  const isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua);
  return isIos && isSafari;
}

export function getInstallState() {
  if (installed || isStandalone()) return 'installed';
  if (deferredPrompt) return 'available';
  if (isIosSafari()) return 'manual';
  return 'unavailable';
}

export function subscribeToInstallState(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Returns 'accepted', 'dismissed', or null when no prompt was available. */
export async function promptInstall() {
  if (!deferredPrompt) return null;

  const event = deferredPrompt;
  // The event can only be used once, whatever the outcome.
  deferredPrompt = null;
  notify();

  event.prompt();
  const { outcome } = await event.userChoice;
  if (outcome === 'accepted') {
    installed = true;
    notify();
  }
  return outcome;
}

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredPrompt = event;
    notify();
  });

  window.addEventListener('appinstalled', () => {
    installed = true;
    deferredPrompt = null;
    notify();
  });
}

/**
 * Registered only for production builds: a worker sitting in front of the Vite
 * dev server serves stale modules and fights HMR.
 */
export function registerServiceWorker() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // An unavailable worker only costs offline support and the install prompt.
    });
  });
}
