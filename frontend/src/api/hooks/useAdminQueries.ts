import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../endpoints/admin';

export function useAdminAlerts(enabled = true) {
  return useQuery({
    queryKey: ['admin', 'alerts'],
    queryFn: () => adminApi.getAlerts(),
    enabled,
    refetchInterval: 10000,
  });
}
