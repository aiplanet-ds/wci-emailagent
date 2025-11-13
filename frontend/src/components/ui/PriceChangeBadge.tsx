import { Badge } from './Badge';

interface PriceChangeBadgeProps {
  isPriceChange: boolean;
  className?: string;
}

export function PriceChangeBadge({ isPriceChange, className }: PriceChangeBadgeProps) {
  if (isPriceChange) {
    return (
      <Badge variant="info" className={className}>
        <span className="flex items-center gap-1">
          <span>💰</span>
          <span>Price Change</span>
        </span>
      </Badge>
    );
  }

  return (
    <Badge variant="default" className={className}>
      <span className="flex items-center gap-1">
        <span>📄</span>
        <span>Not Price Change</span>
      </span>
    </Badge>
  );
}
