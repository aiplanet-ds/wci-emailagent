import { useIsMutating, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { emailApi } from '../services/api';
import type { EmailFilter, FollowupRequest, SendFollowupRequest } from '../types/email';
import { APPROVE_EMAIL_MUTATION_KEY } from './useVendorVerification';

export function useCurrentUser() {
  return useQuery({
    queryKey: ['user'],
    queryFn: () => emailApi.getCurrentUser(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export interface UseEmailsParams {
  filter?: EmailFilter;
  search?: string;
  page?: number;
  pageSize?: number;
  startDate?: string;
  endDate?: string;
}

export function useEmails(params: UseEmailsParams = {}) {
  const { filter, search, page = 1, pageSize = 15, startDate, endDate } = params;
  const isApproveMutating = useIsMutating({ mutationKey: APPROVE_EMAIL_MUTATION_KEY });

  return useQuery({
    queryKey: ['emails', filter, search, page, pageSize, startDate, endDate],
    queryFn: () => emailApi.getEmails({ filter, search, page, pageSize, startDate, endDate }),
    refetchInterval: isApproveMutating > 0 ? false : 10000, // 10s polling for responsive updates
    placeholderData: (previousData) => previousData, // Keep previous data while loading new page
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
      // Invalidate and refetch emails list, detail, and dashboard stats
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['email', variables.messageId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
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

export function useSendFollowup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ messageId, request }: { messageId: string; request: SendFollowupRequest }) =>
      emailApi.sendFollowup(messageId, request),
    onSuccess: (_, variables) => {
      // Invalidate email detail to refresh state
      queryClient.invalidateQueries({ queryKey: ['email', variables.messageId] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      // Refresh dashboard stats for follow-up counts
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
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
    staleTime: 0, // Always refetch to ensure we have latest thread data
    refetchOnMount: 'always', // Refetch when component mounts (switching emails)
  });
}

export function useThreadExtractedData(messageId: string | null) {
  return useQuery({
    queryKey: ['threadExtractedData', messageId],
    queryFn: () => emailApi.getThreadExtractedData(messageId!),
    enabled: !!messageId,
    staleTime: 0, // Always refetch to ensure we have latest thread data
    refetchOnMount: 'always', // Refetch when component mounts (switching emails)
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
