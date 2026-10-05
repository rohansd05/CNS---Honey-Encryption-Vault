import { apiFetch } from '../client';
import type { AdminAlert } from '../types';

export const adminApi = {
  getAlerts: () => apiFetch<AdminAlert[]>('/admin/alerts'),
};
