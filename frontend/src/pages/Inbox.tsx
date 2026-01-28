import { useState, useMemo } from 'react';
import { EmailDetailDrawer } from '../components/detail/EmailDetailDrawer';
import { InboxFilters } from '../components/inbox/InboxFilters';
import { InboxTable, type ViewMode } from '../components/inbox/InboxTable';
import { useEmails } from '../hooks/useEmails';
import type { EmailFilter, InboxDateRangeOption } from '../types/email';

export function Inbox() {
  const [filter, setFilter] = useState<EmailFilter>('all');
  const [search, setSearch] = useState('');
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('thread');

  // Pagination state
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Date range state
  const [dateOption, setDateOption] = useState<InboxDateRangeOption>('all');
  const [customStartDate, setCustomStartDate] = useState<string>();
  const [customEndDate, setCustomEndDate] = useState<string>();

  // Helper to safely parse date string to ISO format
  const safeParseDate = (dateStr: string | undefined, endOfDay = false): string | undefined => {
    if (!dateStr) return undefined;
    try {
      const date = new Date(dateStr);
      // Check if date is valid
      if (isNaN(date.getTime())) return undefined;
      if (endOfDay) {
        date.setHours(23, 59, 59, 999);
      }
      return date.toISOString();
    } catch {
      return undefined;
    }
  };

  // Calculate actual date range from option
  const { startDate, endDate } = useMemo(() => {
    const now = new Date();
    let start: string | undefined;
    let end: string | undefined;

    switch (dateOption) {
      case 'today': {
        const todayStart = new Date(now);
        todayStart.setHours(0, 0, 0, 0);
        const todayEnd = new Date(now);
        todayEnd.setHours(23, 59, 59, 999);
        start = todayStart.toISOString();
        end = todayEnd.toISOString();
        break;
      }
      case 'last7days': {
        const weekAgo = new Date(now);
        weekAgo.setDate(weekAgo.getDate() - 7);
        start = weekAgo.toISOString();
        end = new Date().toISOString();
        break;
      }
      case 'last30days': {
        const monthAgo = new Date(now);
        monthAgo.setDate(monthAgo.getDate() - 30);
        start = monthAgo.toISOString();
        end = new Date().toISOString();
        break;
      }
      case 'last90days': {
        const quarterAgo = new Date(now);
        quarterAgo.setDate(quarterAgo.getDate() - 90);
        start = quarterAgo.toISOString();
        end = new Date().toISOString();
        break;
      }
      case 'custom': {
        start = safeParseDate(customStartDate);
        end = safeParseDate(customEndDate, true);
        break;
      }
      default:
        start = undefined;
        end = undefined;
    }

    return { startDate: start, endDate: end };
  }, [dateOption, customStartDate, customEndDate]);

  // Reset page when filters change
  const handleFilterChange = (newFilter: EmailFilter) => {
    setFilter(newFilter);
    setPage(1);
  };

  const handleSearchChange = (newSearch: string) => {
    setSearch(newSearch);
    setPage(1);
  };

  const handleDateOptionChange = (option: InboxDateRangeOption) => {
    setDateOption(option);
    setPage(1);
  };

  const handleCustomDateChange = (start: string, end: string) => {
    setCustomStartDate(start);
    setCustomEndDate(end);
    setPage(1);
  };

  const { data: emailsData, isLoading, error, isFetching } = useEmails({
    filter,
    search,
    page,
    pageSize,
    startDate,
    endDate
  });

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
          onFilterChange={handleFilterChange}
          search={search}
          onSearchChange={handleSearchChange}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          dateOption={dateOption}
          onDateOptionChange={handleDateOptionChange}
          customStartDate={customStartDate}
          customEndDate={customEndDate}
          onCustomDateChange={handleCustomDateChange}
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
              // Pagination props
              currentPage={emailsData?.page || 1}
              totalPages={emailsData?.total_pages || 1}
              totalThreads={emailsData?.total_threads || 0}
              totalEmails={emailsData?.total || 0}
              hasNext={emailsData?.has_next || false}
              hasPrev={emailsData?.has_prev || false}
              onPageChange={setPage}
              isLoadingPage={isFetching && !isLoading}
            />
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
