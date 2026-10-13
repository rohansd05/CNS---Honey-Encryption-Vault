import { apiFetch } from '../client';
import type {
  CreateShareRequest,
  CreateShareResponse,
  OpenShareResponse,
  ShareInboxItem,
  ShareSentItem,
} from '../types';

export const sharesApi = {
  createShare: (data: CreateShareRequest) =>
    apiFetch<CreateShareResponse>('/shares', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getInbox: () => apiFetch<ShareInboxItem[]>('/shares/inbox'),

  getSent: () => apiFetch<ShareSentItem[]>('/shares/sent'),

  openShare: (id: string) =>
    apiFetch<OpenShareResponse>(`/shares/${id}/open`, {
      method: 'POST',
    }),
};
