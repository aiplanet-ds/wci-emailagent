import { useQuery, useIsMutating } from '@tanstack/react-query';
import { emailApi } from '../services/api';
import type { DashboardStats } from '../types/dashboard';
import { APPROVE_EMAIL_MUTATION_KEY } from './useVendorVerification';

/**
 * Hook to fetch dashboard statistics
 * Auto-refetches every 30 seconds to keep data fresh
 * Pauses polling during approve mutation to prevent race conditions
 */
export function useDashboardStats(startDate?: string, endDate?: string) {
  const isApproveMutating = useIsMutating({ mutationKey: APPROVE_EMAIL_MUTATION_KEY });

  return useQuery<DashboardStats>({
    queryKey: ['dashboard-stats', startDate, endDate],
    queryFn: () => emailApi.getDashboardStats(startDate, endDate),
    staleTime: 30000, // Consider data stale after 30 seconds
    refetchInterval: isApproveMutating > 0 ? false : 30000, // Pause polling during mutation
  });
}
