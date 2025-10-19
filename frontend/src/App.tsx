import { useState, useEffect } from 'react';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { InboxFilters } from './components/inbox/InboxFilters';
import { InboxTable } from './components/inbox/InboxTable';
import { EmailDetailDrawer } from './components/detail/EmailDetailDrawer';
import { useEmails, useCurrentUser } from './hooks/useEmails';
import type { EmailFilter } from './types/email';

function App() {
  const [filter, setFilter] = useState<EmailFilter>('all');
  const [search, setSearch] = useState('');
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);

  const { data: user } = useCurrentUser();
  const { data: emailsData, isLoading, error } = useEmails(filter, search);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (user && !user.authenticated) {
      window.location.href = 'http://localhost:8000/login';
    }
  }, [user]);

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!user.authenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Not Authenticated</h2>
          <p className="text-gray-600 mb-4">Please log in to continue</p>
          <a
            href="http://localhost:8000/login"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Log In
          </a>
        </div>
      </div>
    );
  }

  return (
    <DashboardLayout>
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
        />
      )}
    </DashboardLayout>
  );
}

export default App;
