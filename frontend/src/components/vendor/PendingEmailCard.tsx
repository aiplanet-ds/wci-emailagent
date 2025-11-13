import { Mail, User, Calendar, AlertTriangle, Check, X, Loader2, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { EmailBodyViewer } from '../email/EmailBodyViewer';
import { AttachmentList } from '../email/AttachmentList';
import { useApproveEmail, useRejectEmail } from '../../hooks/useVendorVerification';
import { useRawEmailContent } from '../../hooks/useEmails';
import { formatDate } from '../../lib/utils';
import type { EmailListItem } from '../../types/email';

interface PendingEmailCardProps {
  email: EmailListItem;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

export function PendingEmailCard({ email, isExpanded, onToggleExpand }: PendingEmailCardProps) {
  const approveMutation = useApproveEmail();
  const rejectMutation = useRejectEmail();
  const { data: rawEmail, isLoading: isLoadingRaw } = useRawEmailContent(
    isExpanded ? email.message_id : null
  );

  const handleApprove = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click when clicking approve
    approveMutation.mutate(email.message_id);
  };

  const handleReject = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click when clicking reject
    rejectMutation.mutate(email.message_id);
  };

  const handleCardClick = () => {
    onToggleExpand();
  };

  const handleCloseClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleExpand();
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
    <Card
      className={`p-6 hover:shadow-md transition-all duration-200 cursor-pointer ${
        isExpanded ? 'shadow-lg ring-2 ring-blue-200' : ''
      }`}
      onClick={handleCardClick}
    >
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

        <div className="flex items-center gap-2">
          <Badge variant="warning" className="flex-shrink-0">
            ⚠️ Pending Review
          </Badge>

          {isExpanded && (
            <button
              onClick={handleCloseClick}
              className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100"
              title="Collapse"
            >
              <ChevronUp className="h-5 w-5" />
            </button>
          )}

          {!isExpanded && (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
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

      {/* Email Content (Expanded) */}
      {isExpanded && (
        <div className="mb-4 space-y-4 animate-fadeIn">
          {isLoadingRaw ? (
            <div className="flex items-center justify-center p-8 bg-gray-50 rounded-lg">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400 mr-2" />
              <span className="text-sm text-gray-600">Loading email content...</span>
            </div>
          ) : rawEmail ? (
            <>
              {/* Email Body */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Email Body
                </h4>
                <EmailBodyViewer
                  body={rawEmail.body}
                  bodyType={rawEmail.bodyType}
                />
              </div>

              {/* Attachments */}
              {rawEmail.attachments && rawEmail.attachments.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">
                    Attachments ({rawEmail.attachments.length})
                  </h4>
                  <AttachmentList
                    attachments={rawEmail.attachments}
                    messageId={email.message_id}
                  />
                </div>
              )}
            </>
          ) : (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
              Failed to load email content
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
          <X className="h-4 w-4 mr-2" />
          Reject
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
