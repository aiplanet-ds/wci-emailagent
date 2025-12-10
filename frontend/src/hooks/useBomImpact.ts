import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emailApi } from '../services/api';
import type { BomImpactApprovalRequest } from '../types/email';

/**
 * Hook to fetch BOM impact analysis results for an email
 */
export function useBomImpact(messageId: string | null) {
  return useQuery({
    queryKey: ['bomImpact', messageId],
    queryFn: () => emailApi.getBomImpact(messageId!),
    enabled: !!messageId,
    staleTime: 60 * 1000, // 1 minute
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to approve a specific product's BOM impact for Epicor sync
 */
export function useApproveBomImpact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      messageId,
      productIndex,
      request,
    }: {
      messageId: string;
      productIndex: number;
      request?: BomImpactApprovalRequest;
    }) => emailApi.approveBomImpact(messageId, productIndex, request),
    onSuccess: (_, variables) => {
      // Invalidate BOM impact query to refresh data
      queryClient.invalidateQueries({ queryKey: ['bomImpact', variables.messageId] });
      // Also invalidate email detail in case it shows approval status
      queryClient.invalidateQueries({ queryKey: ['email', variables.messageId] });
    },
  });
}

/**
 * Hook to approve all products in an email for Epicor sync
 */
export function useApproveAllBomImpacts() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      messageId,
      request,
    }: {
      messageId: string;
      request?: BomImpactApprovalRequest;
    }) => emailApi.approveAllBomImpacts(messageId, request),
    onSuccess: (_, variables) => {
      // Invalidate BOM impact query to refresh data
      queryClient.invalidateQueries({ queryKey: ['bomImpact', variables.messageId] });
      // Also invalidate email detail
      queryClient.invalidateQueries({ queryKey: ['email', variables.messageId] });
    },
  });
}

/**
 * Hook to re-run BOM impact analysis for an email
 */
export function useReanalyzeBomImpact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: string) => emailApi.reanalyzeBomImpact(messageId),
    onSuccess: (_, messageId) => {
      // Invalidate BOM impact query to refresh data
      queryClient.invalidateQueries({ queryKey: ['bomImpact', messageId] });
    },
  });
}

