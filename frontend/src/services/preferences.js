/**
 * Per-browser display preferences, stored in cookies.
 *
 * Both navbars toggle the theme, so the read/write/apply trio lives here rather
 * than being duplicated (and drifting) between them.
 */
import { readWithLocalStorageFallback, setCookie } from './cookies.js';

const THEME_COOKIE = 'paxis.theme';
const SIDEBAR_COOKIE = 'paxis.sidebarCollapsed';

// Keys used before the move to cookies.
const THEME_LEGACY = ['theme'];
const SIDEBAR_LEGACY = ['paxis.sidebarCollapsed', 'sarp.sidebarCollapsed'];

export function isDarkTheme() {
  return readWithLocalStorageFallback(THEME_COOKIE, THEME_LEGACY) === 'dark';
}

export function setDarkTheme(dark) {
  setCookie(THEME_COOKIE, dark ? 'dark' : 'light');
}

export function applyTheme(dark) {
  document.body.classList.toggle('dark-mode', dark);
}

export function isSidebarCollapsed() {
  return readWithLocalStorageFallback(SIDEBAR_COOKIE, SIDEBAR_LEGACY) === 'true';
}

export function setSidebarCollapsed(collapsed) {
  setCookie(SIDEBAR_COOKIE, String(collapsed));
}
