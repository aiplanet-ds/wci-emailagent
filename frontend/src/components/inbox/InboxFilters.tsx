import { Calendar, Filter, List, MessageSquare, Search } from 'lucide-react';
import type { EmailFilter, InboxDateRangeOption } from '../../types/email';
import { Input } from '../ui/Input';
import type { ViewMode } from './InboxTable';

interface InboxFiltersProps {
  filter: EmailFilter;
  onFilterChange: (filter: EmailFilter) => void;
  search: string;
  onSearchChange: (search: string) => void;
  viewMode?: ViewMode;
  onViewModeChange?: (mode: ViewMode) => void;
  // Date range filter
  dateOption: InboxDateRangeOption;
  onDateOptionChange: (option: InboxDateRangeOption) => void;
  customStartDate?: string;
  customEndDate?: string;
  onCustomDateChange: (startDate: string, endDate: string) => void;
}

const dateOptions: { value: InboxDateRangeOption; label: string }[] = [
  { value: 'all', label: 'All Time' },
  { value: 'today', label: 'Today' },
  { value: 'last7days', label: 'Last 7 Days' },
  { value: 'last30days', label: 'Last 30 Days' },
  { value: 'last90days', label: 'Last 90 Days' },
  { value: 'custom', label: 'Custom Range' },
];

const filters: { value: EmailFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'price_change', label: 'Price Change' },
  { value: 'non_price_change', label: 'Not Price Change' },
  { value: 'processed', label: 'Processed' },
  { value: 'unprocessed', label: 'Unprocessed' },
  { value: 'pending_verification', label: 'Pending Verification' },
  { value: 'rejected', label: 'Rejected' },
];

export function InboxFilters({
  filter,
  onFilterChange,
  search,
  onSearchChange,
  viewMode = 'thread',
  onViewModeChange,
  dateOption,
  onDateOptionChange,
  customStartDate,
  customEndDate,
  onCustomDateChange
}: InboxFiltersProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* First row: Status filter, Date filter, Search, View mode */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        {/* Status Filter Dropdown */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          <select
            value={filter}
            onChange={(e) => onFilterChange(e.target.value as EmailFilter)}
            className="pl-10 pr-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer min-w-[200px]"
          >
            {filters.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date Range Filter */}
        <div className="relative">
          <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          <select
            value={dateOption}
            onChange={(e) => onDateOptionChange(e.target.value as InboxDateRangeOption)}
            className="pl-10 pr-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer min-w-[160px]"
          >
            {dateOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Search Bar */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search by subject or sender..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* View Mode Toggle */}
        {onViewModeChange && (
          <div className="flex items-center gap-1 bg-gray-100 rounded-md p-1">
            <button
              onClick={() => onViewModeChange('thread')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                viewMode === 'thread'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              title="Thread View - Group emails by conversation"
            >
              <MessageSquare className="h-4 w-4" />
              <span className="hidden sm:inline">Threads</span>
            </button>
            <button
              onClick={() => onViewModeChange('flat')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                viewMode === 'flat'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              title="Flat View - Show all emails individually"
            >
              <List className="h-4 w-4" />
              <span className="hidden sm:inline">Flat</span>
            </button>
          </div>
        )}
      </div>

      {/* Second row: Custom date inputs (only visible when custom is selected) */}
      {dateOption === 'custom' && (
        <div className="flex items-center gap-3 pl-0 sm:pl-0">
          <span className="text-sm text-gray-500">From:</span>
          <input
            type="date"
            value={customStartDate || ''}
            onChange={(e) => onCustomDateChange(e.target.value, customEndDate || '')}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <span className="text-sm text-gray-500">To:</span>
          <input
            type="date"
            value={customEndDate || ''}
            onChange={(e) => onCustomDateChange(customStartDate || '', e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      )}
    </div>
  );
}
