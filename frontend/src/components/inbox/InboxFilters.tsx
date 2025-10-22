import { Search } from 'lucide-react';
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
];

export function InboxFilters({ filter, onFilterChange, search, onSearchChange }: InboxFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-4">
      {/* Filter Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => onFilterChange(f.value)}
            className={`px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors ${
              filter === f.value
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
            }`}
          >
            {f.label}
          </button>
        ))}
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
