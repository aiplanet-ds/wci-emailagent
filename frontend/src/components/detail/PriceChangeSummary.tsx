import { Calendar, FileText, TrendingDown, TrendingUp } from 'lucide-react';
import type { PriceChangeSummary as PriceChangeSummaryType } from '../../types/email';
import { Badge } from '../ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface PriceChangeSummaryProps {
  summary: PriceChangeSummaryType;
}

export function PriceChangeSummary({ summary }: PriceChangeSummaryProps) {
  const getChangeIcon = () => {
    if (summary.change_type === 'increase') return TrendingUp;
    if (summary.change_type === 'decrease') return TrendingDown;
    return FileText;
  };

  const getChangeVariant = () => {
    if (summary.change_type === 'increase') return 'danger';
    if (summary.change_type === 'decrease') return 'success';
    return 'default';
  };

  const ChangeIcon = getChangeIcon();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Price Change Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <ChangeIcon className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
            <div className="flex-1">
              <p className="text-xs text-gray-500">Change Type</p>
              <div className="mt-1">
                {summary.change_type ? (
                  <Badge variant={getChangeVariant()}>
                    {summary.change_type.replace('_', ' ').toUpperCase()}
                  </Badge>
                ) : (
                  <span className="text-sm text-gray-400 italic">Not specified</span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <Calendar className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
            <div className="flex-1">
              <p className="text-xs text-gray-500">Effective Date</p>
              <p className="text-sm text-gray-900 font-medium">
                {summary.effective_date || <span className="text-gray-400 italic">Not provided</span>}
              </p>
            </div>
          </div>

          {summary.reason && (
            <div className="flex items-start gap-2">
              <FileText className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
              <div className="flex-1">
                <p className="text-xs text-gray-500">Reason</p>
                <p className="text-sm text-gray-900">{summary.reason}</p>
              </div>
            </div>
          )}

          {summary.overall_impact && (
            <div className="flex items-start gap-2">
              <FileText className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
              <div className="flex-1">
                <p className="text-xs text-gray-500">Overall Impact</p>
                <p className="text-sm text-gray-900">{summary.overall_impact}</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
