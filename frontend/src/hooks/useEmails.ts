import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { emailApi } from '../services/api';
import type { EmailFilter, FollowupRequest } from '../types/email';

export function useCurrentUser() {
  return useQuery({
    queryKey: ['user'],
    queryFn: () => emailApi.getCurrentUser(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useEmails(filter?: EmailFilter, search?: string) {
  return useQuery({
    queryKey: ['emails', filter, search],
    queryFn: () => emailApi.getEmails(filter, search),
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

export function useEmailDetail(messageId: string | null) {
  return useQuery({
    queryKey: ['email', messageId],
    queryFn: () => emailApi.getEmailDetail(messageId!),
    enabled: !!messageId, // Only run if messageId is provided
  });
}

export function useUpdateEmailProcessed() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ messageId, processed, force = false }: { messageId: string; processed: boolean; force?: boolean }) =>
      emailApi.updateEmailProcessed(messageId, processed, force),
    onSuccess: (_, variables) => {
      // Invalidate and refetch emails list and detail
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['email', variables.messageId] });
    },
  });
}

export function useGenerateFollowup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ messageId, request }: { messageId: string; request: FollowupRequest }) =>
      emailApi.generateFollowup(messageId, request),
    onSuccess: (_, variables) => {
      // Invalidate email detail to refresh state
      queryClient.invalidateQueries({ queryKey: ['email', variables.messageId] });
    },
  });
}

export function useRawEmailContent(messageId: string | null) {
  return useQuery({
    queryKey: ['rawEmail', messageId],
    queryFn: () => emailApi.getRawEmailContent(messageId!),
    enabled: !!messageId, // Only run if messageId is provided
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}

export function useThreadHistory(messageId: string | null) {
  return useQuery({
    queryKey: ['thread', messageId],
    queryFn: () => emailApi.getThreadHistory(messageId!),
    enabled: !!messageId,
    staleTime: 2 * 60 * 1000, // Cache for 2 minutes
  });
}

export function useToggleEmailPin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ messageId, pinned }: { messageId: string; pinned: boolean }) =>
      emailApi.toggleEmailPin(messageId, pinned),
    onSuccess: () => {
      // Invalidate email list to reflect pin status
      queryClient.invalidateQueries({ queryKey: ['emails'] });
    },
  });
}
