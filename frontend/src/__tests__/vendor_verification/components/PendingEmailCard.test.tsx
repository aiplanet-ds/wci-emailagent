import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PendingEmailCard } from '../../../components/vendor/PendingEmailCard'

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

describe('PendingEmailCard', () => {
  const mockEmail = {
    message_id: 'test-msg-123',
    sender: 'unknown@random.com',
    subject: 'Price Update Request',
    received_time: '2025-10-23T10:00:00',
    verification_status: 'pending_review' as const,
    flagged_reason: 'Sender not in verified vendor list',
  }

  it('renders email information correctly', () => {
    render(<PendingEmailCard email={mockEmail} />, { wrapper: createWrapper() })

    expect(screen.getByText('Price Update Request')).toBeInTheDocument()
    expect(screen.getByText(/unknown@random.com/i)).toBeInTheDocument()
    expect(screen.getByText(/Sender not in verified vendor list/i)).toBeInTheDocument()
  })

  it('displays approve and reject buttons', () => {
    render(<PendingEmailCard email={mockEmail} />, { wrapper: createWrapper() })

    expect(screen.getByRole('button', { name: /approve & process/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument()
  })

  it('shows formatted received time', () => {
    render(<PendingEmailCard email={mockEmail} />, { wrapper: createWrapper() })

    // Should show relative time or formatted date
    expect(screen.getByText(/received/i)).toBeInTheDocument()
  })

  it('displays verification badge', () => {
    render(<PendingEmailCard email={mockEmail} />, { wrapper: createWrapper() })

    expect(screen.getByText(/pending review/i)).toBeInTheDocument()
  })
})
