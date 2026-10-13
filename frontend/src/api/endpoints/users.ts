import { apiFetch } from '../client';
import type { UserIdentityResponse } from '../types';

export const usersApi = {
  getIdentity: (username: string) =>
    apiFetch<UserIdentityResponse>(`/users/${encodeURIComponent(username)}/identity`),
};
