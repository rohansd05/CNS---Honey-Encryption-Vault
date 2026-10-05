import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { sharesApi } from '../endpoints/shares';
import type { CreateShareRequest } from '../types';

export function useShareInbox() {
  return useQuery({
    queryKey: ['shares', 'inbox'],
    queryFn: () => sharesApi.getInbox(),
  });
}

export function useShareSent() {
  return useQuery({
    queryKey: ['shares', 'sent'],
    queryFn: () => sharesApi.getSent(),
  });
}

export function useCreateShare() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateShareRequest) => sharesApi.createShare(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['shares', 'sent'] });
    },
  });
}

export function useOpenShare() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (shareId: string) => sharesApi.openShare(shareId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['shares', 'inbox'] });
    },
  });
}
