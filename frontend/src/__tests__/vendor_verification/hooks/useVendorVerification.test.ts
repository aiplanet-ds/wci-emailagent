import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  usePendingEmails,
  useApproveEmail,
  useRejectEmail,
  useVendorCache,
  useRefreshCache,
} from '../../../hooks/useVendorVerification'
import * as api from '../../../services/api'

// Create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useVendorVerification hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('usePendingEmails', () => {
    it('fetches pending emails successfully', async () => {
      const mockData = {
        emails: [
          {
            message_id: 'msg-1',
            sender: 'test@unknown.com',
            subject: 'Test Email',
            verification_status: 'pending_review',
          },
        ],
        total: 1,
      }

      vi.spyOn(api.apiClient, 'getPendingVerificationEmails').mockResolvedValue(mockData)

      const { result } = renderHook(() => usePendingEmails(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual(mockData)
    })

    it('handles error when fetching pending emails', async () => {
      vi.spyOn(api.apiClient, 'getPendingVerificationEmails').mockRejectedValue(
        new Error('Network error')
      )

      const { result } = renderHook(() => usePendingEmails(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })
    })
  })

  describe('useApproveEmail', () => {
    it('approves email successfully', async () => {
      const mockResponse = {
        status: 'approved_and_processing',
        message_id: 'msg-123',
      }

      vi.spyOn(api.apiClient, 'approveAndProcessEmail').mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useApproveEmail(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('msg-123')

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(api.apiClient.approveAndProcessEmail).toHaveBeenCalledWith('msg-123')
    })

    it('handles approval error', async () => {
      vi.spyOn(api.apiClient, 'approveAndProcessEmail').mockRejectedValue(
        new Error('Approval failed')
      )

      const { result } = renderHook(() => useApproveEmail(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('msg-123')

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })
    })
  })

  describe('useRejectEmail', () => {
    it('rejects email successfully', async () => {
      const mockResponse = {
        status: 'rejected',
        message_id: 'msg-456',
      }

      vi.spyOn(api.apiClient, 'rejectEmail').mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useRejectEmail(), {
        wrapper: createWrapper(),
      })

      result.current.mutate('msg-456')

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(api.apiClient.rejectEmail).toHaveBeenCalledWith('msg-456')
    })
  })

  describe('useVendorCache', () => {
    it('fetches vendor cache status successfully', async () => {
      const mockData = {
        vendor_count: 100,
        email_count: 98,
        domain_count: 74,
        ttl_hours: 24,
        is_stale: false,
        last_updated: '2025-10-23T10:00:00',
      }

      vi.spyOn(api.apiClient, 'getVendorCacheStatus').mockResolvedValue(mockData)

      const { result } = renderHook(() => useVendorCache(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual(mockData)
    })
  })

  describe('useRefreshCache', () => {
    it('refreshes vendor cache successfully', async () => {
      const mockResponse = {
        status: 'success',
        cache_data: {
          vendor_count: 105,
          email_count: 103,
        },
      }

      vi.spyOn(api.apiClient, 'refreshVendorCache').mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useRefreshCache(), {
        wrapper: createWrapper(),
      })

      result.current.mutate()

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(api.apiClient.refreshVendorCache).toHaveBeenCalled()
    })

    it('handles cache refresh error', async () => {
      vi.spyOn(api.apiClient, 'refreshVendorCache').mockRejectedValue(
        new Error('Epicor connection failed')
      )

      const { result } = renderHook(() => useRefreshCache(), {
        wrapper: createWrapper(),
      })

      result.current.mutate()

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })
    })
  })
})
