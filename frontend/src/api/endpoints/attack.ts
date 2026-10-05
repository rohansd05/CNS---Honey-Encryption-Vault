import { apiFetch } from '../client';
import type {
  AttackAlarmsResponse,
  AttackStolenVaultResponse,
  DictionaryAttackRequest,
  DictionaryAttackResponse,
  StolenHoneywordsResponse,
} from '../types';

export const attackApi = {
  getStolenVault: () => apiFetch<AttackStolenVaultResponse>('/attack/stolen-vault'),

  runDictionaryAttack: (data: DictionaryAttackRequest) =>
    apiFetch<DictionaryAttackResponse>('/attack/dictionary', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getStolenHoneywords: () =>
    apiFetch<StolenHoneywordsResponse>('/attack/stolen-honeywords'),

  getAlarms: () => apiFetch<AttackAlarmsResponse>('/attack/alarms'),
};
