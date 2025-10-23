import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emailApi } from '../services/api';

/**
 * Hook to fetch pending verification emails
 */
export function usePendingEmails() {
  return useQuery({
    queryKey: ['pending-emails'],
    queryFn: () => emailApi.getPendingVerificationEmails(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

/**
 * Hook to approve and process a flagged email
 */
export function useApproveEmail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: string) => emailApi.approveAndProcessEmail(messageId),
    onSuccess: (_, messageId) => {
      // Invalidate all related queries
      queryClient.invalidateQueries({ queryKey: ['pending-emails'] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['email', messageId] });
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
      // Invalidate pending emails list
      queryClient.invalidateQueries({ queryKey: ['pending-emails'] });
      queryClient.invalidateQueries({ queryKey: ['emails'] });
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
