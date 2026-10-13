// owner: Krrish (T3) — fetch wrapper
// Base URL from VITE_API_BASE_URL env var; Bearer token injected automatically.

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

// A 401 fires this event so AuthProvider can log the user out
const UNAUTHORIZED_EVENT = 'hv:unauthorized';
export function onUnauthorized(cb: () => void) {
  window.addEventListener(UNAUTHORIZED_EVENT, cb);
  return () => {
    window.removeEventListener(UNAUTHORIZED_EVENT, cb);
  };
}

function getBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000') + '/api';
}

let _getToken: (() => string | null) | null = null;
/** Call this once from AuthProvider so the client can read the in-memory token */
export function registerTokenGetter(fn: () => string | null) {
  _getToken = fn;
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail: string | Array<{ msg: string }> };
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d) => d.msg).join('; ');
  } catch {
    // ignore
  }
  return res.statusText || `HTTP ${String(res.status)}`;
}

interface FetchOptions extends RequestInit {
  noAuth?: boolean;
}

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { noAuth = false, headers: extraHeaders = {}, ...rest } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(extraHeaders as Record<string, string>),
  };

  if (!noAuth && _getToken) {
    const tok = _getToken();
    if (tok) headers['Authorization'] = `Bearer ${tok}`;
  }

  const res = await fetch(`${getBaseUrl()}${path}`, { headers, ...rest });

  if (res.status === 401) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    const detail = await parseError(res);
    throw new ApiError(401, detail);
  }

  if (!res.ok) {
    const detail = await parseError(res);
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}
