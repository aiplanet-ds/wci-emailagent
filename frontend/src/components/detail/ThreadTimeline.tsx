import { CheckCircle2, Clock, DollarSign, Layers, Mail, MessageSquare, XCircle } from 'lucide-react';
import { useThreadBomImpact } from '../../hooks/useBomImpact';
import { useThreadHistory } from '../../hooks/useEmails';
import { formatDate } from '../../lib/utils';
import type { ThreadEmail } from '../../types/email';
import { Badge } from '../ui/Badge';

interface ThreadTimelineProps {
  messageId: string;
  currentMessageId: string;
  onEmailSelect: (messageId: string) => void;
}

// Get status icon and color based on verification status
function getStatusInfo(status: string | null) {
  switch (status) {
    case 'verified':
    case 'manually_approved':
      return { icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-50' };
    case 'rejected':
      return { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50' };
    case 'pending_review':
      return { icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-50' };
    default:
      return { icon: Mail, color: 'text-gray-400', bg: 'bg-gray-50' };
  }
}

// Format verification status for display
function formatStatus(status: string | null): string {
  if (!status) return 'Unknown';
  return status
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Format currency
function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function ThreadTimeline({ messageId, currentMessageId, onEmailSelect }: ThreadTimelineProps) {
  const { data: threadData, isLoading, error } = useThreadHistory(messageId);
  const { data: bomData } = useThreadBomImpact(messageId);

  if (isLoading) {
    return (
      <div className="border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <MessageSquare className="h-4 w-4 animate-pulse" />
          <span>Loading thread history...</span>
        </div>
      </div>
    );
  }

  if (error || !threadData) {
    return null;
  }

  // Don't show timeline for single email threads
  if (threadData.total_count <= 1) {
    return null;
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-blue-50 px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-900">
              Conversation Thread
            </span>
          </div>
          <Badge variant="info">{threadData.total_count} emails</Badge>
        </div>
        {threadData.thread_subject && (
          <p className="text-xs text-blue-700 mt-1 truncate">
            {threadData.thread_subject}
          </p>
        )}
      </div>

      {/* Thread BOM Impact Summary */}
      {bomData && bomData.total_parts_affected > 0 && (
        <div className="bg-orange-50 px-4 py-3 border-b border-gray-200">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="h-4 w-4 text-orange-600" />
            <span className="text-sm font-medium text-orange-900">
              Thread BOM Impact Summary
            </span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="bg-white rounded p-2">
              <div className="text-gray-500">Parts Affected</div>
              <div className="font-semibold text-gray-900">{bomData.total_parts_affected}</div>
            </div>
            <div className="bg-white rounded p-2">
              <div className="text-gray-500">Emails w/ BOM</div>
              <div className="font-semibold text-gray-900">{bomData.emails_with_bom_data}</div>
            </div>
            <div className="bg-white rounded p-2">
              <div className="flex items-center gap-1 text-gray-500">
                <DollarSign className="h-3 w-3" />
                Annual Impact
              </div>
              <div className="font-semibold text-orange-700">
                {formatCurrency(bomData.total_annual_impact)}
              </div>
            </div>
          </div>
          {Object.keys(bomData.aggregated_impacts).length > 0 && (
            <div className="mt-2 text-xs text-orange-700">
              <span className="font-medium">Parts:</span>{' '}
              {Object.keys(bomData.aggregated_impacts).slice(0, 3).join(', ')}
              {Object.keys(bomData.aggregated_impacts).length > 3 && (
                <span> +{Object.keys(bomData.aggregated_impacts).length - 3} more</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Timeline */}
      <div className="p-4">
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

          {/* Timeline items */}
          <div className="space-y-4">
            {threadData.emails.map((email: ThreadEmail, index: number) => {
              const isCurrentEmail = email.message_id === currentMessageId;
              const statusInfo = getStatusInfo(email.verification_status);
              const StatusIcon = statusInfo.icon;

              return (
                <div
                  key={email.message_id}
                  onClick={() => onEmailSelect(email.message_id)}
                  className={`relative flex items-start gap-3 pl-8 cursor-pointer group ${
                    isCurrentEmail ? 'opacity-100' : 'opacity-70 hover:opacity-100'
                  }`}
                >
                  {/* Timeline dot */}
                  <div
                    className={`absolute left-2 w-4 h-4 rounded-full border-2 ${
                      isCurrentEmail
                        ? 'bg-blue-500 border-blue-500'
                        : `${statusInfo.bg} border-gray-300 group-hover:border-blue-400`
                    }`}
                  />

                  {/* Content */}
                  <div
                    className={`flex-1 rounded-lg p-3 transition-colors ${
                      isCurrentEmail
                        ? 'bg-blue-50 border border-blue-200'
                        : email.is_outgoing
                        ? 'bg-purple-50 border border-purple-100 group-hover:border-purple-200'
                        : 'bg-gray-50 border border-transparent group-hover:border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900 truncate">
                            {email.is_outgoing ? 'You' : email.sender}
                          </span>
                          {email.is_outgoing && (
                            <Badge variant="purple" className="text-xs">Sent</Badge>
                          )}
                          {!email.is_outgoing && email.is_reply && (
                            <Badge variant="info" className="text-xs">Re</Badge>
                          )}
                          {!email.is_outgoing && email.is_forward && (
                            <Badge variant="info" className="text-xs">Fwd</Badge>
                          )}
                          {isCurrentEmail && (
                            <Badge variant="success" className="text-xs">Current</Badge>
                          )}
                        </div>
                        <p className="text-xs text-gray-600 mt-0.5 truncate">
                          {email.subject}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <StatusIcon className={`h-4 w-4 ${statusInfo.color}`} />
                        <span className="text-xs text-gray-500">
                          {email.received_at ? formatDate(email.received_at) : 'Unknown'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs text-gray-500">
                        Status: {formatStatus(email.verification_status)}
                      </span>
                      <span className="text-xs text-gray-400">•</span>
                      <span className="text-xs text-gray-500">
                        #{index + 1} in thread
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

