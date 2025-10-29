import { Search, Filter } from 'lucide-react';
import { Input } from '../ui/Input';
import type { EmailFilter } from '../../types/email';

interface InboxFiltersProps {
  filter: EmailFilter;
  onFilterChange: (filter: EmailFilter) => void;
  search: string;
  onSearchChange: (search: string) => void;
}

const filters: { value: EmailFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'price_change', label: 'Price Change' },
  { value: 'non_price_change', label: 'Not Price Change' },
  { value: 'processed', label: 'Processed' },
  { value: 'unprocessed', label: 'Unprocessed' },
  { value: 'pending_verification', label: 'Pending Verification' },
  { value: 'rejected', label: 'Rejected' },
];

export function InboxFilters({ filter, onFilterChange, search, onSearchChange }: InboxFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-4">
      {/* Filter Dropdown */}
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
    </div>
  );
}
