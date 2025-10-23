import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VerificationBadge } from '../../../components/ui/VerificationBadge'

describe('VerificationBadge', () => {
  it('renders verified status correctly', () => {
    render(<VerificationBadge status="verified" />)
    expect(screen.getByText('Verified')).toBeInTheDocument()
    expect(screen.getByText('✅')).toBeInTheDocument()
  })

  it('renders pending_review status correctly', () => {
    render(<VerificationBadge status="pending_review" />)
    expect(screen.getByText('Pending Review')).toBeInTheDocument()
    expect(screen.getByText('⚠️')).toBeInTheDocument()
  })

  it('renders manually_approved status correctly', () => {
    render(<VerificationBadge status="manually_approved" />)
    expect(screen.getByText('Manually Approved')).toBeInTheDocument()
    expect(screen.getByText('👤')).toBeInTheDocument()
  })

  it('renders rejected status correctly', () => {
    render(<VerificationBadge status="rejected" />)
    expect(screen.getByText('Rejected')).toBeInTheDocument()
    expect(screen.getByText('❌')).toBeInTheDocument()
  })

  it('renders unverified status correctly', () => {
    render(<VerificationBadge status="unverified" />)
    expect(screen.getByText('Unverified')).toBeInTheDocument()
    expect(screen.getByText('🚫')).toBeInTheDocument()
  })

  it('shows verification method when showMethod is true', () => {
    render(
      <VerificationBadge
        status="verified"
        method="exact_email"
        showMethod={true}
      />
    )
    expect(screen.getByText(/exact_email/i)).toBeInTheDocument()
  })

  it('does not show verification method by default', () => {
    render(
      <VerificationBadge
        status="verified"
        method="exact_email"
      />
    )
    expect(screen.queryByText(/exact_email/i)).not.toBeInTheDocument()
  })

  it('applies correct CSS classes for verified status', () => {
    const { container } = render(<VerificationBadge status="verified" />)
    const badge = container.querySelector('.inline-flex')
    expect(badge).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('applies correct CSS classes for pending status', () => {
    const { container } = render(<VerificationBadge status="pending_review" />)
    const badge = container.querySelector('.inline-flex')
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800')
  })

  it('applies correct CSS classes for rejected status', () => {
    const { container } = render(<VerificationBadge status="rejected" />)
    const badge = container.querySelector('.inline-flex')
    expect(badge).toHaveClass('bg-red-100', 'text-red-800')
  })
})
