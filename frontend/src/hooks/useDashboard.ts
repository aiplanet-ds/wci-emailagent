import { useQuery } from '@tanstack/react-query';
import { emailApi } from '../services/api';
import type { DashboardStats } from '../types/dashboard';

/**
 * Hook to fetch dashboard statistics
 * Auto-refetches every 30 seconds to keep data fresh
 */
export function useDashboardStats(startDate?: string, endDate?: string) {
  return useQuery<DashboardStats>({
    queryKey: ['dashboard-stats', startDate, endDate],
    queryFn: () => emailApi.getDashboardStats(startDate, endDate),
    staleTime: 30000, // Consider data stale after 30 seconds
    refetchInterval: 30000, // Auto-refetch every 30 seconds
  });
}
