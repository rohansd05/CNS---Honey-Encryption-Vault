import { useMutation, useQuery } from '@tanstack/react-query';
import { attackApi } from '../endpoints/attack';
import type { DictionaryAttackRequest } from '../types';

export function useStolenVault(enabled = true) {
  return useQuery({
    queryKey: ['attack', 'stolen-vault'],
    queryFn: () => attackApi.getStolenVault(),
    enabled,
  });
}

export function useRunDictionaryAttack() {
  return useMutation({
    mutationFn: (data: DictionaryAttackRequest) => attackApi.runDictionaryAttack(data),
  });
}

export function useStolenHoneywords(enabled = true) {
  return useQuery({
    queryKey: ['attack', 'stolen-honeywords'],
    queryFn: () => attackApi.getStolenHoneywords(),
    enabled,
  });
}

export function useAttackAlarms(enabled = true) {
  return useQuery({
    queryKey: ['attack', 'alarms'],
    queryFn: () => attackApi.getAlarms(),
    enabled,
    refetchInterval: 3000,
  });
}
