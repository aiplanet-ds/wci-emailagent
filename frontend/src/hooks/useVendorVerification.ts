import { useQuery, useMutation, useQueryClient, useIsMutating } from '@tanstack/react-query';
import { emailApi } from '../services/api';

// Mutation key for approve email - exported for use in other hooks to pause polling
export const APPROVE_EMAIL_MUTATION_KEY = ['approve-email'];

/**
 * Hook to fetch pending verification emails
 * Automatically pauses polling during approve mutation to prevent race conditions
 */
export function usePendingEmails() {
  const isApproveMutating = useIsMutating({ mutationKey: APPROVE_EMAIL_MUTATION_KEY });

  return useQuery({
    queryKey: ['pending-emails'],
    queryFn: () => emailApi.getPendingVerificationEmails(),
    refetchInterval: isApproveMutating > 0 ? false : 30000, // Pause polling during mutation
    staleTime: 10000, // Consider data fresh for 10 seconds
  });
}

/**
 * Hook to approve and process a flagged email
 */
export function useApproveEmail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: APPROVE_EMAIL_MUTATION_KEY,
    mutationFn: (messageId: string) => emailApi.approveAndProcessEmail(messageId),
    onSuccess: (_, messageId) => {
      // Invalidate all related queries with exact matching
      queryClient.invalidateQueries({ queryKey: ['pending-emails'], exact: true });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['email', messageId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    },
  });
}

/**
 * Hook to reject a flagged email
 */
export function useRejectEmail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: string) => emailApi.rejectEmail(messageId),
    onSuccess: () => {
      // Invalidate pending emails list with exact matching
      queryClient.invalidateQueries({ queryKey: ['pending-emails'], exact: true });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    },
  });
}

/**
 * Hook to fetch vendor cache status
 */
export function useVendorCache() {
  return useQuery({
    queryKey: ['vendor-cache'],
    queryFn: () => emailApi.getVendorCacheStatus(),
    staleTime: 60000, // Consider data fresh for 1 minute
  });
}

/**
 * Hook to refresh vendor cache
 */
export function useRefreshCache() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => emailApi.refreshVendorCache(),
    onSuccess: () => {
      // Invalidate vendor cache query to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['vendor-cache'] });
    },
  });
}
