import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { Settings } from '../../../pages/Settings'
import * as useVendorVerification from '../../../hooks/useVendorVerification'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Settings Page', () => {
  it('renders page title and description', () => {
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
      isPending: false,
    } as any)

    render(<Settings />, { wrapper: createWrapper() })

    expect(screen.getByText(/settings/i)).toBeInTheDocument()
    expect(screen.getByText(/vendor verification/i)).toBeInTheDocument()
  })

  it('renders vendor cache status section', () => {
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
      isPending: false,
    } as any)

    render(<Settings />, { wrapper: createWrapper() })

    expect(screen.getByText(/vendor cache management/i)).toBeInTheDocument()
  })

  it('displays configuration information', () => {
    vi.spyOn(useVendorVerification, 'useVendorCache').mockReturnValue({
      data: {
        vendor_count: 100,
        email_count: 98,
        domain_count: 74,
        ttl_hours: 24,
        domain_matching_enabled: true,
      },
      isLoading: false,
      error: null,
    } as any)

    vi.spyOn(useVendorVerification, 'useRefreshCache').mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any)

    render(<Settings />, { wrapper: createWrapper() })

    expect(screen.getByText(/configuration/i)).toBeInTheDocument()
    expect(screen.getByText(/domain matching/i)).toBeInTheDocument()
  })

  it('shows token savings impact section', () => {
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
      isPending: false,
    } as any)

    render(<Settings />, { wrapper: createWrapper() })

    expect(screen.getByText(/token savings impact/i)).toBeInTheDocument()
  })
})
