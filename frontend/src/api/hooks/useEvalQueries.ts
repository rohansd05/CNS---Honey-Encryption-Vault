import { useQuery } from '@tanstack/react-query';
import { evalApi } from '../endpoints/eval';

export function useEvalSummary(enabled = true) {
  return useQuery({
    queryKey: ['eval', 'summary'],
    queryFn: () => evalApi.getSummary(),
    enabled,
  });
}
