import { apiFetch } from '../client';
import type {
  AddEntryRequest,
  AddEntryResponse,
  ExportVaultBlob,
  UnlockRequest,
  UnlockResponse,
  UpdateEntryRequest,
  UpdateEntryResponse,
} from '../types';

export const vaultApi = {
  unlock: (data: UnlockRequest) =>
    apiFetch<UnlockResponse>('/vault/unlock', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  addEntry: (data: AddEntryRequest) =>
    apiFetch<AddEntryResponse>('/vault/entries', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateEntry: (id: string, data: UpdateEntryRequest) =>
    apiFetch<UpdateEntryResponse>(`/vault/entries/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteEntry: (id: string) =>
    apiFetch<undefined>(`/vault/entries/${id}`, {
      method: 'DELETE',
    }),

  exportVault: () => apiFetch<ExportVaultBlob>('/vault/export'),
};
