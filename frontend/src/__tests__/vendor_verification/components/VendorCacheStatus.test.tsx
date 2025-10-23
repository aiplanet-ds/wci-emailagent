import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { VendorCacheStatus } from '../../../components/vendor/VendorCacheStatus'
import * as useVendorVerification from '../../../hooks/useVendorVerification'

// Create a wrapper with QueryClient
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

describe('VendorCacheStatus', () => {
  it('renders loading state initially', () => {
    vi.spyOn(useVendorVerification, 'useVendorCache').mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any)

    vi.spyOn(useVendorVerification, 'useRefreshCache').mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any)

    render(<VendorCacheStatus />, { wrapper: createWrapper() })
    expect(screen.getByText('Loading cache status...')).toBeInTheDocument()
  })

  it('renders cache statistics correctly', () => {
    const mockData = {
      vendor_count: 100,
      email_count: 98,
      domain_count: 74,
      ttl_hours: 24,
      last_updated: '2025-10-23T10:00:00',
      is_stale: false,
      next_refresh: '2025-10-24T10:00:00',
      domain_matching_enabled: true,
    }

    vi.spyOn(useVendorVerification, 'useVendorCache').mockReturnValue({
      data: mockData,
      isLoading: false,
      error: null,
    } as any)

    vi.spyOn(useVendorVerification, 'useRefreshCache').mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any)

    render(<VendorCacheStatus />, { wrapper: createWrapper() })

    expect(screen.getByText('100')).toBeInTheDocument()
    expect(screen.getByText('98')).toBeInTheDocument()
    expect(screen.getByText('74')).toBeInTheDocument()
    expect(screen.getByText('24 hours')).toBeInTheDocument()
  })

  it('shows refresh button and triggers refresh on click', async () => {
    const user = userEvent.setup()
    const mockRefresh = vi.fn()

    vi.spyOn(useVendorVerification, 'useVendorCache').mockReturnValue({
      data: {
        vendor_count: 100,
        email_count: 98,
        domain_count: 74,
        ttl_hours: 24,
      },
      isLoading: false,
      error: null,
    } as any)

    vi.spyOn(useVendorVerification, 'useRefreshCache').mockReturnValue({
      mutate: mockRefresh,
      isPending: false,
    } as any)

    render(<VendorCacheStatus />, { wrapper: createWrapper() })

    const refreshButton = screen.getByRole('button', { name: /refresh/i })
    await user.click(refreshButton)

    expect(mockRefresh).toHaveBeenCalled()
  })

  it('shows loading state on refresh button when refreshing', () => {
    vi.spyOn(useVendorVerification, 'useVendorCache').mockReturnValue({
      data: {
        vendor_count: 100,
        email_count: 98,
        domain_count: 74,
        ttl_hours: 24,
      },
      isLoading: false,
      error: null,
    } as any)

    vi.spyOn(useVendorVerification, 'useRefreshCache').mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
    } as any)

    render(<VendorCacheStatus />, { wrapper: createWrapper() })

    const refreshButton = screen.getByRole('button', { name: /refreshing/i })
    expect(refreshButton).toBeDisabled()
  })

  it('renders error state correctly', () => {
    vi.spyOn(useVendorVerification, 'useVendorCache').mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load cache'),
    } as any)

    vi.spyOn(useVendorVerification, 'useRefreshCache').mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any)

    render(<VendorCacheStatus />, { wrapper: createWrapper() })

    expect(screen.getByText(/error loading cache status/i)).toBeInTheDocument()
  })

  it('displays stale cache warning when cache is stale', () => {
    vi.spyOn(useVendorVerification, 'useVendorCache').mockReturnValue({
      data: {
        vendor_count: 100,
        email_count: 98,
        domain_count: 74,
        ttl_hours: 24,
        is_stale: true,
      },
      isLoading: false,
      error: null,
    } as any)

    vi.spyOn(useVendorVerification, 'useRefreshCache').mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any)

    render(<VendorCacheStatus />, { wrapper: createWrapper() })

    expect(screen.getByText(/cache is stale/i)).toBeInTheDocument()
  })
})
