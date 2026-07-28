// Distinct from VITE_API_URL (which docker-compose.yml sets for vite.config.ts's
// dev-server proxy target only) — Vite exposes VITE_-prefixed process env vars
// to the client bundle too, and that one holds a Docker-internal hostname
// ("backend") that the browser can't resolve. In dev this is left unset, so
// relative paths keep going through the proxy; in production it's set to the
// deployed backend's public URL.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

let accessToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

async function refreshAccessToken(): Promise<string | null> {
  const res = await fetch(apiUrl('/api/v1/auth/refresh'), { method: 'POST', credentials: 'include' });
  if (!res.ok) return null;
  const data = await res.json();
  accessToken = data.access_token as string;
  return accessToken;
}

/** Fetch wrapper that attaches the access token and retries once after a silent refresh on 401. */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const doFetch = () =>
    fetch(apiUrl(path), {
      ...options,
      credentials: 'include',
      headers: {
        ...options.headers,
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    });

  let res = await doFetch();

  if (res.status === 401 && accessToken !== null) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      res = await doFetch();
    } else {
      onUnauthorized?.();
    }
  }

  return res;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiFetchJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body?.detail ?? `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
