import { apiFetch } from '../client';
import type { EvalSummaryResponse } from '../types';

export const evalApi = {
  getSummary: () => apiFetch<EvalSummaryResponse>('/eval/summary'),
};
