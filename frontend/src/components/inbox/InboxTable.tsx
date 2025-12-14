import { AlertCircle, CheckCircle2, ChevronDown, ChevronRight, ChevronsDownUp, ChevronsUpDown, Mail, MessageSquare, Package, Pin } from 'lucide-react';
import React, { useCallback, useMemo, useState } from 'react';
import { useToggleEmailPin } from '../../hooks/useEmails';
import { formatDate } from '../../lib/utils';
import type { EmailListItem } from '../../types/email';
import { Badge } from '../ui/Badge';
import { PriceChangeBadge } from '../ui/PriceChangeBadge';
import { VerificationBadge } from '../ui/VerificationBadge';

export type ViewMode = 'thread' | 'flat';

interface InboxTableProps {
  emails: EmailListItem[];
  selectedEmailId: string | null;
  onEmailSelect: (emailId: string) => void;
  viewMode?: ViewMode;
}

interface ThreadGroup {
  conversationId: string | null;
  threadSubject: string;
  emails: EmailListItem[];
  latestDate: string;
}

// Get thread status summary for aggregated display
function getThreadStatusSummary(emails: EmailListItem[]): { text: string; variant: 'success' | 'warning' | 'danger' | 'info' | 'default' } {
  const statusCounts: Record<string, number> = {};

  emails.forEach(e => {
    const status = e.verification_status || 'unknown';
    statusCounts[status] = (statusCounts[status] || 0) + 1;
  });

  const total = emails.length;
  const verified = (statusCounts['verified'] || 0) + (statusCounts['manually_approved'] || 0);
  const pending = statusCounts['pending_review'] || 0;
  const rejected = statusCounts['rejected'] || 0;

  if (verified === total) {
    return { text: 'All verified', variant: 'success' };
  }
  if (rejected > 0 && rejected === total) {
    return { text: 'All rejected', variant: 'danger' };
  }
  if (pending > 0) {
    return { text: `${pending} pending`, variant: 'warning' };
  }
  if (verified > 0) {
    return { text: `${verified}/${total} verified`, variant: 'info' };
  }
  return { text: 'Mixed status', variant: 'default' };
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

export function InboxTable({ emails, selectedEmailId, onEmailSelect, viewMode = 'thread' }: InboxTableProps) {
  const [expandedThreads, setExpandedThreads] = useState<Set<string>>(new Set());
  const togglePin = useToggleEmailPin();

  const threadGroups = useMemo(() => groupEmailsByThread(emails), [emails]);

  // Get all conversation IDs for expand/collapse all
  const allConversationIds = useMemo(() => {
    return threadGroups
      .filter(g => g.conversationId && g.emails.length > 1)
      .map(g => g.conversationId as string);
  }, [threadGroups]);

  const toggleThread = useCallback((conversationId: string) => {
    setExpandedThreads((prev) => {
      const next = new Set(prev);
      if (next.has(conversationId)) {
        next.delete(conversationId);
      } else {
        next.add(conversationId);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedThreads(new Set(allConversationIds));
  }, [allConversationIds]);

  const collapseAll = useCallback(() => {
    setExpandedThreads(new Set());
  }, []);

  const hasThreads = allConversationIds.length > 0;
  const allExpanded = hasThreads && expandedThreads.size === allConversationIds.length;

  if (emails.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <Mail className="h-12 w-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-900">No emails found</h3>
        <p className="text-sm text-gray-500 mt-1">Try adjusting your filters or search query</p>
      </div>
    );
  }

  const handlePinClick = (e: React.MouseEvent, messageId: string, isPinned: boolean) => {
    e.stopPropagation();
    togglePin.mutate({ messageId, pinned: !isPinned });
  };

  const renderEmailRow = (email: EmailListItem, isThreadChild: boolean = false) => (
    <tr
      key={email.message_id}
      onClick={() => onEmailSelect(email.message_id)}
      className={`cursor-pointer hover:bg-gray-50 transition-colors ${
        selectedEmailId === email.message_id ? 'bg-blue-50' : ''
      } ${isThreadChild ? 'bg-gray-50/50' : ''}`}
    >
      <td className="px-2 py-4 w-10">
        <button
          onClick={(e) => handlePinClick(e, email.message_id, email.pinned || false)}
          className={`p-1 rounded hover:bg-gray-200 transition-colors ${
            email.pinned ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'
          }`}
          title={email.pinned ? 'Unpin email' : 'Pin email'}
        >
          <Pin className="h-4 w-4" fill={email.pinned ? 'currentColor' : 'none'} />
        </button>
      </td>
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

  // Flat view - render all emails without grouping
  if (viewMode === 'flat') {
    return (
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="w-10 px-2 py-3"></th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subject</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sender</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Info</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {emails.map((email) => renderEmailRow(email, false))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Expand/Collapse All Controls */}
      {hasThreads && (
        <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-end gap-2">
          <button
            onClick={allExpanded ? collapseAll : expandAll}
            className="flex items-center gap-1 text-xs text-gray-600 hover:text-gray-900 transition-colors"
          >
            {allExpanded ? (
              <>
                <ChevronsDownUp className="h-4 w-4" />
                <span>Collapse All</span>
              </>
            ) : (
              <>
                <ChevronsUpDown className="h-4 w-4" />
                <span>Expand All</span>
              </>
            )}
          </button>
        </div>
      )}
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="w-10 px-2 py-3"></th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subject</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sender</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Info</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {threadGroups.map((group) => {
            const isThread = group.emails.length > 1 && group.conversationId;
            const isExpanded = group.conversationId ? expandedThreads.has(group.conversationId) : false;
            const latestEmail = group.emails[group.emails.length - 1];

            if (!isThread) {
              return renderEmailRow(group.emails[0]);
            }

            const statusSummary = getThreadStatusSummary(group.emails);

            // Check if any email in thread is pinned
            const isThreadPinned = group.emails.some(e => e.pinned);

            return (
              <React.Fragment key={`thread-${group.conversationId}`}>
                <tr
                  className="cursor-pointer hover:bg-gray-50 transition-colors bg-gray-50/30"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleThread(group.conversationId!);
                  }}
                >
                  <td className="px-2 py-4 w-10">
                    <button
                      onClick={(e) => handlePinClick(e, latestEmail.message_id, isThreadPinned)}
                      className={`p-1 rounded hover:bg-gray-200 transition-colors ${
                        isThreadPinned ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'
                      }`}
                      title={isThreadPinned ? 'Unpin thread' : 'Pin thread'}
                    >
                      <Pin className="h-4 w-4" fill={isThreadPinned ? 'currentColor' : 'none'} />
                    </button>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-gray-500" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-gray-500" />
                      )}
                      <MessageSquare className="h-4 w-4 text-blue-500 flex-shrink-0" />
                      <span className="text-sm font-medium text-gray-900 line-clamp-2">{group.threadSubject}</span>
                      <Badge variant="info" className="text-xs">{group.emails.length} emails</Badge>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">{latestEmail.sender}</div>
                    <div className="text-xs text-gray-500">{latestEmail.supplier_name}</div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{formatDate(latestEmail.date)}</td>
                  <td className="px-6 py-4">
                    <Badge variant={statusSummary.variant} className="text-xs">{statusSummary.text}</Badge>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Package className="h-4 w-4" />
                      <span>{group.emails.reduce((sum, e) => sum + e.products_count, 0)} products</span>
                    </div>
                  </td>
                </tr>
                {isExpanded && group.emails.map((email) => renderEmailRow(email, true))}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
