import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { PendingVerification } from '../../../pages/PendingVerification'
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

describe('PendingVerification Page', () => {
  it('renders page title and description', () => {
    vi.spyOn(useVendorVerification, 'usePendingEmails').mockReturnValue({
      data: { emails: [], total: 0 },
      isLoading: false,
      error: null,
    } as any)

    render(<PendingVerification />, { wrapper: createWrapper() })

    expect(screen.getByText(/pending verification/i)).toBeInTheDocument()
    expect(screen.getByText(/review and approve flagged emails/i)).toBeInTheDocument()
  })

  it('shows loading state', () => {
    vi.spyOn(useVendorVerification, 'usePendingEmails').mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any)

    render(<PendingVerification />, { wrapper: createWrapper() })

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows empty state when no pending emails', () => {
    vi.spyOn(useVendorVerification, 'usePendingEmails').mockReturnValue({
      data: { emails: [], total: 0 },
      isLoading: false,
      error: null,
    } as any)

    render(<PendingVerification />, { wrapper: createWrapper() })

    expect(screen.getByText(/no pending emails/i)).toBeInTheDocument()
    expect(screen.getByText(/✓/)).toBeInTheDocument()
  })

  it('renders pending email cards when emails exist', () => {
    const mockEmails = [
      {
        message_id: 'msg-1',
        sender: 'test1@unknown.com',
        subject: 'Price Update 1',
        verification_status: 'pending_review' as const,
        received_time: '2025-10-23T10:00:00',
      },
      {
        message_id: 'msg-2',
        sender: 'test2@unknown.com',
        subject: 'Price Update 2',
        verification_status: 'pending_review' as const,
        received_time: '2025-10-23T11:00:00',
      },
    ]

    vi.spyOn(useVendorVerification, 'usePendingEmails').mockReturnValue({
      data: { emails: mockEmails, total: 2 },
      isLoading: false,
      error: null,
    } as any)

    render(<PendingVerification />, { wrapper: createWrapper() })

    expect(screen.getByText('Price Update 1')).toBeInTheDocument()
    expect(screen.getByText('Price Update 2')).toBeInTheDocument()
    expect(screen.getByText(/2 pending emails/i)).toBeInTheDocument()
  })

  it('shows search input', () => {
    vi.spyOn(useVendorVerification, 'usePendingEmails').mockReturnValue({
      data: { emails: [], total: 0 },
      isLoading: false,
      error: null,
    } as any)

    render(<PendingVerification />, { wrapper: createWrapper() })

    expect(screen.getByPlaceholderText(/search emails/i)).toBeInTheDocument()
  })

  it('displays token savings information', () => {
    vi.spyOn(useVendorVerification, 'usePendingEmails').mockReturnValue({
      data: { emails: [], total: 0 },
      isLoading: false,
      error: null,
    } as any)

    render(<PendingVerification />, { wrapper: createWrapper() })

    expect(screen.getByText(/token savings/i)).toBeInTheDocument()
  })

  it('renders error state', () => {
    vi.spyOn(useVendorVerification, 'usePendingEmails').mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load'),
    } as any)

    render(<PendingVerification />, { wrapper: createWrapper() })

    expect(screen.getByText(/error/i)).toBeInTheDocument()
  })
})
