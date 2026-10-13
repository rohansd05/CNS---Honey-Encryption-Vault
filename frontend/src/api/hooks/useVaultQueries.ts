import { useMutation, useQuery } from '@tanstack/react-query';
import { vaultApi } from '../endpoints/vault';
import type { AddEntryRequest, UnlockRequest, UpdateEntryRequest } from '../types';

export function useUnlockVault() {
  return useMutation({
    mutationFn: (data: UnlockRequest) => vaultApi.unlock(data),
  });
}

export function useAddVaultEntry() {
  return useMutation({
    mutationFn: (data: AddEntryRequest) => vaultApi.addEntry(data),
  });
}

export function useUpdateVaultEntry() {
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateEntryRequest }) =>
      vaultApi.updateEntry(id, data),
  });
}

export function useDeleteVaultEntry() {
  return useMutation({
    mutationFn: (id: string) => vaultApi.deleteEntry(id),
  });
}

export function useExportVault(enabled = false) {
  return useQuery({
    queryKey: ['vault', 'export'],
    queryFn: () => vaultApi.exportVault(),
    enabled,
  });
}
