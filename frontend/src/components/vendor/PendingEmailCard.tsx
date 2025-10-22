import { useState } from 'react';
import { Mail, User, Calendar, AlertTriangle, Check, X, Loader2 } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { useApproveEmail, useRejectEmail } from '../../hooks/useVendorVerification';
import { formatDate } from '../../lib/utils';
import type { EmailListItem } from '../../types/email';

interface PendingEmailCardProps {
  email: EmailListItem;
}

export function PendingEmailCard({ email }: PendingEmailCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const approveMutation = useApproveEmail();
  const rejectMutation = useRejectEmail();

  const handleApprove = () => {
    approveMutation.mutate(email.message_id);
  };

  const handleReject = () => {
    rejectMutation.mutate(email.message_id);
  };

  const isProcessing = approveMutation.isPending || rejectMutation.isPending;
  const isSuccess = approveMutation.isSuccess;

  if (isSuccess) {
    return (
      <Card className="p-6 bg-green-50 border-green-200">
        <div className="flex items-center gap-3 text-green-800">
          <Check className="h-6 w-6" />
          <div>
            <p className="font-medium">Email Approved & Processed</p>
            <p className="text-sm text-green-700">
              AI extraction completed successfully for: {email.subject}
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Mail className="h-5 w-5 text-gray-400" />
            <h3 className="font-semibold text-gray-900 line-clamp-1">{email.subject}</h3>
          </div>

          <div className="flex flex-wrap gap-3 text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <User className="h-4 w-4" />
              <span>{email.sender}</span>
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              <span>{formatDate(email.date)}</span>
            </div>
          </div>
        </div>

        <Badge variant="warning" className="flex-shrink-0">
          ⚠️ Pending Review
        </Badge>
      </div>

      {/* Flagged Reason */}
      {email.flagged_reason && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
          <div className="text-sm text-yellow-800">
            <p className="font-medium">Flagged Reason:</p>
            <p>{email.flagged_reason}</p>
          </div>
        </div>
      )}

      {/* Additional Info (Expandable) */}
      {email.supplier_name && email.supplier_name !== 'Unknown' && (
        <div className="mb-4">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {isExpanded ? 'Hide' : 'Show'} Details
          </button>

          {isExpanded && (
            <div className="mt-2 p-3 bg-gray-50 rounded-md text-sm space-y-1">
              <div>
                <span className="font-medium text-gray-700">Supplier:</span>{' '}
                <span className="text-gray-900">{email.supplier_name}</span>
              </div>
              {email.products_count > 0 && (
                <div>
                  <span className="font-medium text-gray-700">Products:</span>{' '}
                  <span className="text-gray-900">{email.products_count}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button
          onClick={handleApprove}
          disabled={isProcessing}
          className="flex-1 bg-green-600 hover:bg-green-700 text-white"
        >
          {approveMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Check className="h-4 w-4 mr-2" />
              Approve & Process
            </>
          )}
        </Button>

        <Button
          onClick={handleReject}
          disabled={isProcessing}
          variant="outline"
          className="flex-1 border-red-300 text-red-700 hover:bg-red-50"
        >
          {rejectMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Rejecting...
            </>
          ) : (
            <>
              <X className="h-4 w-4 mr-2" />
              Reject
            </>
          )}
        </Button>
      </div>

      {/* Error Messages */}
      {approveMutation.isError && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
          ❌ Failed to approve email. Please try again.
        </div>
      )}

      {rejectMutation.isError && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
          ❌ Failed to reject email. Please try again.
        </div>
      )}
    </Card>
  );
}
