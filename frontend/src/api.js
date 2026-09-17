/* ==========================================================================
   api.js -- the single place that talks to the FastAPI backend.
   --------------------------------------------------------------------------
   Every screen needs the same three things:
     1. put the server address in front of the path
     2. attach the login token
     3. turn an error response into a readable message
   Doing it once here means no page ever repeats it.
   ========================================================================== */

// Where the backend lives. import.meta.env.VITE_API_URL lets you override
// this later (for deployment) without editing code.
export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const TOKEN_KEY = 'skillswap_token';

/* --------------------------------------------------------------- token -- */
// localStorage is a small permanent store inside the browser. Keeping the
// token there is what keeps you signed in across page refreshes.
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

/* ----------------------------------------------------------------- core -- */
/**
 * Make one request to the backend.
 *
 * `async` means this function does something slow (network) and returns a
 * promise. Callers write `await api.get(...)` to wait for the answer.
 */
async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };

  const token = getToken();
  if (auth && token) {
    // This is the exact header the backend's HTTPBearer looks for.
    headers.Authorization = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    // fetch only throws for network-level problems -- server down, no wifi.
    throw new Error('Cannot reach the server. Is the backend running on port 8000?');
  }

  // 204 No Content: success, but deliberately nothing to read.
  if (res.status === 204) return null;

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    // A 401 means the token is missing, expired or invalid. Drop it so the
    // app falls back to the login screen instead of retrying forever.
    if (res.status === 401) clearToken();
    throw new Error(extractMessage(data, res.status));
  }

  return data;
}

/**
 * FastAPI reports errors in a few different shapes. This flattens them all
 * into one readable sentence.
 */
function extractMessage(data, status) {
  if (typeof data === 'string' && data) return data;

  const detail = data?.detail;
  if (typeof detail === 'string') return detail;

  // Pydantic validation errors arrive as a list of objects.
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : '';
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .join(', ');
  }

  return `Request failed (${status}).`;
}

/* ------------------------------------------------------------- helpers -- */
/** Turn { q: 'react', page: 2 } into '?q=react&page=2', skipping empties. */
export function qs(params = {}) {
  const usable = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== ''
  );
  if (!usable.length) return '';
  return '?' + new URLSearchParams(usable).toString();
}

export const api = {
  get:   (path, opts)       => request(path, { ...opts }),
  post:  (path, body, opts) => request(path, { method: 'POST',   body, ...opts }),
  patch: (path, body, opts) => request(path, { method: 'PATCH',  body, ...opts }),
  del:   (path, opts)       => request(path, { method: 'DELETE', ...opts }),
};
