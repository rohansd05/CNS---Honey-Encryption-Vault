import { apiFetch } from '../client';
import type { StrengthRequest, StrengthResponse } from '../types';

export const utilsApi = {
  estimateStrength: (data: StrengthRequest) =>
    apiFetch<StrengthResponse>('/utils/strength', {
      method: 'POST',
      body: JSON.stringify(data),
      noAuth: true,
    }),
};
