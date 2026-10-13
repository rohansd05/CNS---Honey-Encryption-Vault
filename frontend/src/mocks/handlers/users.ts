// owner: Krrish (T3) — mock handlers for Users API
import { http, HttpResponse } from 'msw';
import type { UserIdentityResponse } from '@/api/types';

export const usersHandlers = [
  // GET /api/users/:username/identity
  http.get('/api/users/:username/identity', ({ params }) => {
    const { username } = params;
    if (username === 'nonexistent' || username === 'unknown') {
      return HttpResponse.json({ detail: 'User not found' }, { status: 404 });
    }

    const response: UserIdentityResponse = {
      username: username as string,
      public_key_pem: `-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE+mock+key+${username as string}==\n-----END PUBLIC KEY-----`,
      certificate_pem: `-----BEGIN CERTIFICATE-----\nMIIBojCCAUqgAwIBAgIU+mock+cert+${username as string}==\n-----END CERTIFICATE-----`,
    };
    return HttpResponse.json(response);
  }),
];
