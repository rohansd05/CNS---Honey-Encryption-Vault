// owner: Krrish (T3) — mock handlers for Auth API
import { http, HttpResponse } from 'msw';
import type { LoginRequest, RegisterRequest } from '@/api/types';

export const authHandlers = [
  // POST /api/auth/register
  http.post('/api/auth/register', async ({ request }) => {
    const body = (await request.json()) as RegisterRequest;

    if (body.login_password === body.master_password) {
      return HttpResponse.json(
        { detail: 'Login password and master password must be different.' },
        { status: 422 },
      );
    }

    if (body.username === 'demo' || body.username === 'admin') {
      return HttpResponse.json(
        { detail: `Username '${body.username}' is already taken.` },
        { status: 409 },
      );
    }

    return HttpResponse.json(
      { id: `usr-${Date.now().toString()}`, username: body.username },
      { status: 201 },
    );
  }),

  // POST /api/auth/login
  http.post('/api/auth/login', async ({ request }) => {
    const body = (await request.json()) as LoginRequest;

    if (body.username === 'demo' && body.login_password === 'demo-login-pass') {
      return HttpResponse.json({
        access_token: 'mock-jwt-token-demo',
        token_type: 'bearer',
        user: { id: 'usr-demo-1', username: 'demo', is_admin: false },
      });
    }

    if (body.username === 'admin' && body.login_password === 'admin-pass') {
      return HttpResponse.json({
        access_token: 'mock-jwt-token-admin',
        token_type: 'bearer',
        user: { id: 'usr-admin-1', username: 'admin', is_admin: true },
      });
    }

    return HttpResponse.json(
      { detail: 'Invalid credentials' },
      { status: 401 },
    );
  }),

  // GET /api/auth/me
  http.get('/api/auth/me', ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }

    const token = authHeader.slice(7);
    const isAdmin = token.includes('admin');

    return HttpResponse.json({
      id: isAdmin ? 'usr-admin-1' : 'usr-demo-1',
      username: isAdmin ? 'admin' : 'demo',
      is_admin: isAdmin,
      created_at: '2026-10-01T00:00:00Z',
      entry_count: 8,
    });
  }),
];
