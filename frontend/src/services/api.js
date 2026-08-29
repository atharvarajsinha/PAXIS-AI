import {
  clearLocalStorageKeys,
  deleteCookie,
  readWithLocalStorageFallback,
  setCookie,
} from './cookies.js';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const TOKEN_COOKIE = 'paxis.token';
// Keys the token lived under before it moved into a cookie.
const TOKEN_LEGACY_KEYS = ['paxis.token', 'sarp.token'];

export function getToken() {
  // Carries an existing session across instead of silently signing the learner
  // out on their next visit.
  return readWithLocalStorageFallback(TOKEN_COOKIE, TOKEN_LEGACY_KEYS) || null;
}

export function setToken(token) {
  clearLocalStorageKeys(TOKEN_LEGACY_KEYS);
  if (token) setCookie(TOKEN_COOKIE, token);
  else deleteCookie(TOKEN_COOKIE);
}

export function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Token ${token}` } : {};
}

/** Turn a DRF error body into one readable sentence. */
export function readApiError(body, fallback = 'Something went wrong. Please try again.') {
  if (!body) return fallback;
  if (typeof body === 'string') return body;
  if (body.detail) return String(body.detail);
  if (body.error) return String(body.error);

  const messages = [];
  for (const [field, value] of Object.entries(body)) {
    const text = Array.isArray(value) ? value.join(' ') : String(value);
    messages.push(field === 'non_field_errors' ? text : `${field.replace(/_/g, ' ')}: ${text}`);
  }
  return messages.length ? messages.join(' ') : fallback;
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function apiRequest(path, { method = 'GET', body, auth = true } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(auth ? authHeaders() : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  if (response.status === 204) return null;

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(readApiError(payload), response.status);
  }
  return payload;
}
