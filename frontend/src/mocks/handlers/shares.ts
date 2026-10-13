// owner: Krrish (T3) — mock handlers for Shares API
import { http, HttpResponse } from 'msw';
import type {
  CreateShareRequest,
  CreateShareResponse,
  OpenShareResponse,
  ShareInboxItem,
  ShareSentItem,
} from '@/api/types';

const MOCK_INBOX: ShareInboxItem[] = [
  {
    share_id: 'sh-in-1',
    sender: 'alice',
    service: 'github.com',
    created_at: '2026-10-02T14:00:00Z',
    opened_at: null,
  },
  {
    share_id: 'sh-in-2',
    sender: 'bob',
    service: 'aws.amazon.com',
    created_at: '2026-10-03T09:30:00Z',
    opened_at: '2026-10-03T10:00:00Z',
  },
  {
    share_id: 'sh-in-tampered',
    sender: 'mallory',
    service: 'cryptobank.io',
    created_at: '2026-10-04T12:00:00Z',
    opened_at: null,
  },
];

const MOCK_SENT: ShareSentItem[] = [
  {
    share_id: 'sh-sent-1',
    recipient: 'charlie',
    service: 'netflix.com',
    created_at: '2026-10-04T16:45:00Z',
    opened_at: null,
  },
];

export const sharesHandlers = [
  // POST /api/shares
  http.post('/api/shares', async ({ request }) => {
    const body = (await request.json()) as CreateShareRequest;
    if (!body.entry_id || !body.recipient_username || !body.master_password) {
      return HttpResponse.json({ detail: 'Missing required fields' }, { status: 422 });
    }

    if (body.recipient_username === 'self' || body.recipient_username === 'demo') {
      return HttpResponse.json({ detail: 'Cannot share with yourself' }, { status: 422 });
    }

    if (body.recipient_username === 'nonexistent') {
      return HttpResponse.json({ detail: 'User not found' }, { status: 404 });
    }

    const response: CreateShareResponse = {
      share_id: `sh-${Date.now().toString()}`,
    };
    return HttpResponse.json(response, { status: 201 });
  }),

  // GET /api/shares/inbox
  http.get('/api/shares/inbox', () => {
    return HttpResponse.json<ShareInboxItem[]>(MOCK_INBOX);
  }),

  // GET /api/shares/sent
  http.get('/api/shares/sent', () => {
    return HttpResponse.json<ShareSentItem[]>(MOCK_SENT);
  }),

  // POST /api/shares/:id/open
  http.post('/api/shares/:id/open', ({ params }) => {
    const shareId = params.id as string;
    if (shareId === 'nonexistent') {
      return HttpResponse.json({ detail: 'Share not found' }, { status: 404 });
    }

    if (shareId === 'sh-in-tampered') {
      const tamperedResponse: OpenShareResponse = {
        service: 'cryptobank.io',
        username: null,
        password: null,
        sender: 'mallory',
        signature_valid: false,
        certificate_valid: false,
        certificate_subject: 'CN=mallory',
        certificate_issuer: 'CN=HoneyVault Issuing CA',
      };
      return HttpResponse.json(tamperedResponse);
    }

    const item = MOCK_INBOX.find((s) => s.share_id === shareId);
    const service = item?.service ?? 'github.com';
    const sender = item?.sender ?? 'alice';

    const response: OpenShareResponse = {
      service,
      username: `${sender}_shared_user`,
      password: 'SharedSecret2026!P256',
      sender,
      signature_valid: true,
      certificate_valid: true,
      certificate_subject: `CN=${sender}`,
      certificate_issuer: 'CN=HoneyVault Issuing CA',
    };
    return HttpResponse.json(response);
  }),
];
