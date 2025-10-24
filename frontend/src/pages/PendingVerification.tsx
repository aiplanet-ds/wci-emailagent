import { AlertTriangle, Search, CheckCircle } from 'lucide-react';
import { useState } from 'react';
import { PendingEmailCard } from '../components/vendor/PendingEmailCard';
import { Input } from '../components/ui/Input';
import { usePendingEmails } from '../hooks/useVendorVerification';

export function PendingVerification() {
  const [search, setSearch] = useState('');
  const { data, isLoading, error } = usePendingEmails();

  // Filter emails by verification status and search
  const filteredEmails = data?.emails.filter((email) => {
    // First, ensure email is truly pending verification
    if (email.verification_status !== 'pending_review') return false;

    // Then apply search filter
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      email.subject.toLowerCase().includes(searchLower) ||
      email.sender.toLowerCase().includes(searchLower) ||
      (email.supplier_name && email.supplier_name.toLowerCase().includes(searchLower))
    );
  });

  const pendingCount = filteredEmails?.length || 0;

  return (
    <div className="px-6 py-6 space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <AlertTriangle className="h-8 w-8 text-yellow-600" />
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Pending Verification
              {pendingCount > 0 && (
                <span className="ml-3 inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
                  {pendingCount}
                </span>
              )}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Emails from unverified senders requiring manual approval
            </p>
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <p className="text-sm text-blue-800">
            💡 <strong>Token Savings:</strong> These emails were not automatically processed to save AI costs.
            Approve them to trigger AI extraction, or reject to ignore.
          </p>
        </div>
      </div>

      {/* Search Bar */}
      {pendingCount > 0 && (
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search by subject, sender, or supplier..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="text-gray-500">Loading pending emails...</div>
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <div className="text-red-500">Error loading pending emails. Please try again.</div>
        </div>
      ) : pendingCount === 0 ? (
        /* Empty State */
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            All Clear!
          </h3>
          <p className="text-gray-600 mb-4">
            {search
              ? 'No pending emails match your search'
              : 'No emails pending verification at this time'}
          </p>
          {search && (
            <button
              onClick={() => setSearch('')}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Clear search
            </button>
          )}
        </div>
      ) : (
        /* Email List */
        <div className="space-y-4">
          {filteredEmails?.map((email) => (
            <PendingEmailCard key={email.message_id} email={email} />
          ))}
        </div>
      )}

      {/* Stats Footer */}
      {pendingCount > 0 && (
        <div className="text-sm text-gray-600">
          Showing {pendingCount} pending email{pendingCount !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
