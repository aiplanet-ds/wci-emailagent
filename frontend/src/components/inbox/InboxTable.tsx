import { AlertCircle, CheckCircle2, ChevronDown, ChevronRight, Mail, MessageSquare, Package } from 'lucide-react';
import { useMemo, useState } from 'react';
import { formatDate } from '../../lib/utils';
import type { EmailListItem } from '../../types/email';
import { Badge } from '../ui/Badge';
import { PriceChangeBadge } from '../ui/PriceChangeBadge';
import { VerificationBadge } from '../ui/VerificationBadge';

interface InboxTableProps {
  emails: EmailListItem[];
  selectedEmailId: string | null;
  onEmailSelect: (emailId: string) => void;
}

interface ThreadGroup {
  conversationId: string | null;
  threadSubject: string;
  emails: EmailListItem[];
  latestDate: string;
}

// Group emails by conversation_id
function groupEmailsByThread(emails: EmailListItem[]): ThreadGroup[] {
  const threadMap = new Map<string, EmailListItem[]>();
  const noThreadEmails: EmailListItem[] = [];

  emails.forEach((email) => {
    if (email.conversation_id) {
      const existing = threadMap.get(email.conversation_id) || [];
      existing.push(email);
      threadMap.set(email.conversation_id, existing);
    } else {
      noThreadEmails.push(email);
    }
  });

  const groups: ThreadGroup[] = [];

  // Add threaded groups
  threadMap.forEach((threadEmails, conversationId) => {
    // Sort by date ascending within thread
    threadEmails.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    const latestEmail = threadEmails[threadEmails.length - 1];
    groups.push({
      conversationId,
      threadSubject: latestEmail.thread_subject || latestEmail.subject,
      emails: threadEmails,
      latestDate: latestEmail.date,
    });
  });

  // Add non-threaded emails as single-email groups
  noThreadEmails.forEach((email) => {
    groups.push({
      conversationId: null,
      threadSubject: email.subject,
      emails: [email],
      latestDate: email.date,
    });
  });

  // Sort groups by latest date descending
  groups.sort((a, b) => new Date(b.latestDate).getTime() - new Date(a.latestDate).getTime());

  return groups;
}

export function InboxTable({ emails, selectedEmailId, onEmailSelect }: InboxTableProps) {
  const [expandedThreads, setExpandedThreads] = useState<Set<string>>(new Set());

  const threadGroups = useMemo(() => groupEmailsByThread(emails), [emails]);

  const toggleThread = (conversationId: string) => {
    setExpandedThreads((prev) => {
      const next = new Set(prev);
      if (next.has(conversationId)) {
        next.delete(conversationId);
      } else {
        next.add(conversationId);
      }
      return next;
    });
  };

  if (emails.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <Mail className="h-12 w-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-900">No emails found</h3>
        <p className="text-sm text-gray-500 mt-1">Try adjusting your filters or search query</p>
      </div>
    );
  }

  const renderEmailRow = (email: EmailListItem, isThreadChild: boolean = false) => (
    <tr
      key={email.message_id}
      onClick={() => onEmailSelect(email.message_id)}
      className={`cursor-pointer hover:bg-gray-50 transition-colors ${
        selectedEmailId === email.message_id ? 'bg-blue-50' : ''
      } ${isThreadChild ? 'bg-gray-50/50' : ''}`}
    >
      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          {isThreadChild && <div className="w-4" />}
          <Mail className="h-4 w-4 text-gray-400 flex-shrink-0" />
          <span className="text-sm font-medium text-gray-900 line-clamp-2">
            {email.subject}
          </span>
          {(email.is_reply || email.is_forward) && (
            <Badge variant="info" className="text-xs">
              {email.is_reply ? 'Re' : 'Fwd'}
            </Badge>
          )}
        </div>
      </td>
      <td className="px-6 py-4">
        <div className="text-sm text-gray-900">{email.sender}</div>
        <div className="text-xs text-gray-500">{email.supplier_name}</div>
      </td>
      <td className="px-6 py-4 text-sm text-gray-500">
        {formatDate(email.date)}
      </td>
      <td className="px-6 py-4">
        <div className="flex gap-2 flex-wrap">
          {email.verification_status && (
            <VerificationBadge status={email.verification_status} />
          )}
          {(email.verification_status === 'verified' || email.verification_status === 'manually_approved')
            && email.llm_detection_performed && email.is_price_change !== null && (
            <PriceChangeBadge isPriceChange={email.is_price_change} />
          )}
          {(email.verification_status === 'verified' || email.verification_status === 'manually_approved')
            && email.is_price_change === true && (
            email.epicor_synced ? (
              <Badge variant="success">Processed</Badge>
            ) : (
              <Badge variant="warning">Unprocessed</Badge>
            )
          )}
        </div>
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {email.needs_info && (
            <div className="flex items-center gap-1 text-yellow-600">
              <AlertCircle className="h-4 w-4" />
              <span>{email.missing_fields_count} missing</span>
            </div>
          )}
          {email.has_epicor_sync && (
            <div className="flex items-center gap-1 text-green-600">
              <CheckCircle2 className="h-4 w-4" />
              <span>{email.epicor_success_count} synced</span>
            </div>
          )}
          <div className="flex items-center gap-1">
            <Package className="h-4 w-4" />
            <span>{email.products_count} products</span>
          </div>
        </div>
      </td>
    </tr>
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Subject
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Sender
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Info
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {threadGroups.map((group) => {
            const isThread = group.emails.length > 1 && group.conversationId;
            const isExpanded = group.conversationId ? expandedThreads.has(group.conversationId) : false;
            const latestEmail = group.emails[group.emails.length - 1];

            if (!isThread) {
              // Single email - render normally
              return renderEmailRow(group.emails[0]);
            }

            // Thread group - render with expand/collapse
            return (
              <>
                {/* Thread header row */}
                <tr
                  key={`thread-${group.conversationId}`}
                  className="cursor-pointer hover:bg-gray-50 transition-colors bg-gray-50/30"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleThread(group.conversationId!);
                  }}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-gray-500" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-gray-500" />
                      )}
                      <MessageSquare className="h-4 w-4 text-blue-500 flex-shrink-0" />
                      <span className="text-sm font-medium text-gray-900 line-clamp-2">
                        {group.threadSubject}
                      </span>
                      <Badge variant="info" className="text-xs">
                        {group.emails.length} emails
                      </Badge>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">{latestEmail.sender}</div>
                    <div className="text-xs text-gray-500">{latestEmail.supplier_name}</div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDate(latestEmail.date)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-xs text-gray-500">Click to expand</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Package className="h-4 w-4" />
                      <span>
                        {group.emails.reduce((sum, e) => sum + e.products_count, 0)} products
                      </span>
                    </div>
                  </td>
                </tr>
                {/* Thread child emails (when expanded) */}
                {isExpanded && group.emails.map((email) => renderEmailRow(email, true))}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
