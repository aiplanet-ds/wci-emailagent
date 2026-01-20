import { useState } from 'react';
import { EmailDetailDrawer } from '../components/detail/EmailDetailDrawer';
import { InboxFilters } from '../components/inbox/InboxFilters';
import { InboxTable, type ViewMode } from '../components/inbox/InboxTable';
import { useEmails } from '../hooks/useEmails';
import type { EmailFilter } from '../types/email';

export function Inbox() {
  const [filter, setFilter] = useState<EmailFilter>('all');
  const [search, setSearch] = useState('');
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('thread');

  const { data: emailsData, isLoading, error } = useEmails(filter, search);

  return (
    <>
      <div className="px-6 py-6 space-y-6">
        {/* Page Header */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Inbox</h2>
          <p className="text-sm text-gray-600 mt-1">
            Manage supplier price-change notifications
          </p>
        </div>

        {/* Filters */}
        <InboxFilters
          filter={filter}
          onFilterChange={setFilter}
          search={search}
          onSearchChange={setSearch}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />

        {/* Email List */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="text-gray-500">Loading emails...</div>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <div className="text-red-500">Error loading emails. Please try again.</div>
          </div>
        ) : (
          <>
            <InboxTable
              emails={emailsData?.emails || []}
              selectedEmailId={selectedEmailId}
              onEmailSelect={setSelectedEmailId}
              viewMode={viewMode}
            />

            {/* Stats */}
            <div className="text-sm text-gray-600">
              Showing {emailsData?.emails.length || 0} of {emailsData?.total || 0} emails
            </div>
          </>
        )}
      </div>

      {/* Email Detail Drawer */}
      {selectedEmailId && (
        <EmailDetailDrawer
          messageId={selectedEmailId}
          onClose={() => setSelectedEmailId(null)}
          onEmailSelect={setSelectedEmailId}
        />
      )}
    </>
  );
}
