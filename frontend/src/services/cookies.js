/**
 * Thin wrapper over `document.cookie`.
 *
 * Every read and write is guarded: a browser with cookies disabled must degrade
 * to "nothing persists" rather than throwing on boot.
 */

export const ONE_YEAR = 365 * 24 * 60 * 60;

export function getCookie(name) {
  try {
    const prefix = `${encodeURIComponent(name)}=`;
    const hit = document.cookie.split('; ').find((part) => part.startsWith(prefix));
    return hit ? decodeURIComponent(hit.slice(prefix.length)) : null;
  } catch {
    return null;
  }
}

export function setCookie(name, value, maxAge = ONE_YEAR) {
  try {
    const attributes = [
      `${encodeURIComponent(name)}=${encodeURIComponent(value)}`,
      'path=/',
      `max-age=${maxAge}`,
      // Lax still travels on top-level navigation, so an installed shortcut or a
      // shared link opens already signed in.
      'SameSite=Lax',
    ];
    // Browsers drop Secure cookies over plain http, which would break localhost.
    if (window.location.protocol === 'https:') attributes.push('Secure');
    document.cookie = attributes.join('; ');
  } catch {
    // Cookies refused; the value simply will not survive this page load.
  }
}

export function deleteCookie(name) {
  try {
    document.cookie = `${encodeURIComponent(name)}=; path=/; max-age=0; SameSite=Lax`;
  } catch {
    // Nothing to clean up if the store was never writable.
  }
}

/**
 * Reads a cookie, falling back to a pre-cookie localStorage value and moving it
 * across on first use so the change does not sign anyone out or reset their
 * preferences.
 */
export function readWithLocalStorageFallback(cookieName, legacyKeys, maxAge = ONE_YEAR) {
  const current = getCookie(cookieName);
  if (current !== null) return current;

  try {
    for (const key of legacyKeys) {
      const legacy = localStorage.getItem(key);
      if (legacy !== null) {
        setCookie(cookieName, legacy, maxAge);
        legacyKeys.forEach((stale) => localStorage.removeItem(stale));
        return legacy;
      }
    }
  } catch {
    // Storage unavailable: treat it as "nothing stored".
  }
  return null;
}

export function clearLocalStorageKeys(keys) {
  try {
    keys.forEach((key) => localStorage.removeItem(key));
  } catch {
    // Nothing to clean up.
  }
}
