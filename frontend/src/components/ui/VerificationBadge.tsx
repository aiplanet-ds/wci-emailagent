import { Badge } from './Badge';

interface VerificationBadgeProps {
  status: string;
  method?: string | null;
  showMethod?: boolean;
  className?: string;
}

const STATUS_CONFIG = {
  verified: {
    icon: '✅',
    text: 'Verified',
    variant: 'success' as const,
  },
  pending_review: {
    icon: '⚠️',
    text: 'Pending Review',
    variant: 'warning' as const,
  },
  manually_approved: {
    icon: '👤',
    text: 'Manually Approved',
    variant: 'info' as const,
  },
  rejected: {
    icon: '❌',
    text: 'Rejected',
    variant: 'danger' as const,
  },
  unverified: {
    icon: '⚠️',
    text: 'Unverified',
    variant: 'warning' as const,
  },
};

const METHOD_LABELS = {
  exact_email: 'Email Match',
  domain_match: 'Domain Match',
  manual_approval: 'Manual',
  thread_inheritance: 'Thread',
};

export function VerificationBadge({
  status,
  method,
  showMethod = false,
  className,
}: VerificationBadgeProps) {
  const config = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.pending_review;

  return (
    <Badge variant={config.variant} className={className}>
      <span className="flex items-center gap-1">
        <span>{config.icon}</span>
        <span>{config.text}</span>
        {showMethod && method && (
          <span className="text-[10px] opacity-75">
            ({METHOD_LABELS[method as keyof typeof METHOD_LABELS] || method})
          </span>
        )}
      </span>
    </Badge>
  );
}
