// owner: Krrish (T3) — mock handlers for Admin API
import { http, HttpResponse } from 'msw';
import type { AdminAlert } from '@/api/types';

const MOCK_ALERTS: AdminAlert[] = [
  {
    id: 'alt-1',
    username: 'demo',
    kind: 'HONEYWORD_LOGIN',
    severity: 'critical',
    sweetword_index: 4,
    source_ip: '198.51.100.42',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    created_at: '2026-10-04T12:00:00Z',
  },
  {
    id: 'alt-2',
    username: 'bob',
    kind: 'HONEYWORD_LOGIN',
    severity: 'critical',
    sweetword_index: 7,
    source_ip: '203.0.113.19',
    user_agent: 'curl/7.88.1',
    created_at: '2026-10-04T15:30:00Z',
  },
];

export const adminHandlers = [
  // GET /api/admin/alerts
  http.get('/api/admin/alerts', ({ request }) => {
    const auth = request.headers.get('Authorization');
    if (!auth || !auth.includes('admin')) {
      return HttpResponse.json({ detail: 'Forbidden: admin access required' }, { status: 403 });
    }
    return HttpResponse.json<AdminAlert[]>(MOCK_ALERTS);
  }),
];
