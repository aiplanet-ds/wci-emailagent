# Price-Change Inbox Dashboard - Implementation Guide

## Status: Backend Complete ✅ | Frontend In Progress 🚧

### Completed Components

#### Backend (✅ Complete)
1. **Email State Service** - `/services/email_state_service.py`
   - Manages processed status, missing fields, follow-up drafts
   - JSON file-based storage in `/data/email_states.json`

2. **Validation Service** - `/services/validation_service.py`
   - Detects missing required fields
   - Validates Epicor sync readiness

3. **AI Follow-up Generator** - `/extractor.py`
   - `generate_followup_email()` function
   - Uses Azure OpenAI (same as extraction)

4. **API Router** - `/routers/emails.py`
   - `GET /api/emails` - List emails with filters
   - `GET /api/emails/:id` - Get email details
   - `PATCH /api/emails/:id` - Toggle processed (syncs to Epicor)
   - `POST /api/emails/:id/followup` - Generate AI follow-up

5. **Main App Updates** - `/start.py`
   - CORS enabled for React (localhost:5173)
   - API router integrated
   - `/api/user` endpoint for authentication check

#### Frontend (🚧 In Progress)
1. **Project Setup** ✅
   - Vite + React + TypeScript
   - Tailwind CSS configured
   - Dependencies installed

2. **Type Definitions** ✅
   - `/frontend/src/types/email.ts` - Complete type system

3. **API Client** ✅
   - `/frontend/src/services/api.ts` - Axios client with credentials
   - `/frontend/src/hooks/useEmails.ts` - React Query hooks

4. **Utilities** ✅
   - `/frontend/src/lib/utils.ts` - Format functions, cn() helper

5. **UI Components** 🚧
   - `/frontend/src/components/ui/Badge.tsx` ✅

---

## Remaining Frontend Work

### 1. Create Remaining UI Components

**File: `/frontend/src/components/ui/Button.tsx`**
```typescript
import { cn } from '../../lib/utils';
import { ButtonHTMLAttributes, forwardRef } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50';

    const variants = {
      default: 'bg-primary text-white hover:bg-primary/90',
      outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
      ghost: 'hover:bg-accent hover:text-accent-foreground',
      destructive: 'bg-red-500 text-white hover:bg-red-600',
    };

    const sizes = {
      sm: 'h-8 px-3 text-sm',
      md: 'h-10 px-4 py-2',
      lg: 'h-11 px-8',
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      />
    );
  }
);

export { Button };
```

**File: `/frontend/src/components/ui/Input.tsx`**
```typescript
import { cn } from '../../lib/utils';
import { InputHTMLAttributes, forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

export { Input };
```

**File: `/frontend/src/components/ui/Card.tsx`**
```typescript
import { cn } from '../../lib/utils';

function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />;
}

function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('text-2xl font-semibold leading-none tracking-tight', className)} {...props} />;
}

function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-6 pt-0', className)} {...props} />;
}

export { Card, CardHeader, CardTitle, CardContent };
```

### 2. Create Main Layout Component

**File: `/frontend/src/components/layout/DashboardLayout.tsx`**
```typescript
import { Mail, LogOut } from 'lucide-react';
import { useCurrentUser } from '../../hooks/useEmails';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { data: user } = useCurrentUser();

  const handleLogout = () => {
    window.location.href = 'http://localhost:8000/logout';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mail className="h-8 w-8 text-blue-600" />
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Price-Change Inbox</h1>
              <p className="text-sm text-gray-500">Supplier Email Management</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {user?.authenticated && (
              <>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">{user.name}</p>
                  <p className="text-xs text-gray-500">{user.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  Logout
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-[1920px]">
        {children}
      </main>
    </div>
  );
}
```

### 3. Create Inbox Components

**File: `/frontend/src/components/inbox/InboxFilters.tsx`**
```typescript
import { Search } from 'lucide-react';
import { Input } from '../ui/Input';
import type { EmailFilter } from '../../types/email';

interface InboxFiltersProps {
  filter: EmailFilter;
  onFilterChange: (filter: EmailFilter) as void;
  search: string;
  onSearchChange: (search: string) => void;
}

const filters: { value: EmailFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'price_change', label: 'Price Change' },
  { value: 'non_price_change', label: 'Not Price Change' },
  { value: 'processed', label: 'Processed' },
  { value: 'unprocessed', label: 'Unprocessed' },
];

export function InboxFilters({ filter, onFilterChange, search, onSearchChange }: InboxFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-4">
      {/* Filter Tabs */}
      <div className="flex gap-2 overflow-x-auto">
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
```

**File: `/frontend/src/components/inbox/InboxTable.tsx`**
```typescript
import { Mail, AlertCircle, CheckCircle2, Package } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { formatDate } from '../../lib/utils';
import type { EmailListItem } from '../../types/email';

interface InboxTableProps {
  emails: EmailListItem[];
  selectedEmailId: string | null;
  onEmailSelect: (emailId: string) => void;
}

export function InboxTable({ emails, selectedEmailId, onEmailSelect }: InboxTableProps) {
  if (emails.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <Mail className="h-12 w-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-900">No emails found</h3>
        <p className="text-sm text-gray-500 mt-1">Try adjusting your filters or search query</p>
      </div>
    );
  }

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
          {emails.map((email) => (
            <tr
              key={email.message_id}
              onClick={() => onEmailSelect(email.message_id)}
              className={`cursor-pointer hover:bg-gray-50 transition-colors ${
                selectedEmailId === email.message_id ? 'bg-blue-50' : ''
              }`}
            >
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900">{email.subject}</span>
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
                <div className="flex gap-2">
                  {email.is_price_change && (
                    <Badge variant="info">Price Change</Badge>
                  )}
                  {email.processed && (
                    <Badge variant="success">Processed</Badge>
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
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Next Steps to Complete

1. Create detail drawer components (EmailDetailDrawer, SupplierInfo, PriceChangeSummary, ProductsTable)
2. Create MissingFieldsChecklist component
3. Create FollowupModal component
4. Create main App.tsx with React Query provider
5. Update vite.config.ts with proxy settings
6. Create .env file with VITE_API_BASE_URL
7. Test the complete workflow

## Running the Application

### Backend:
```bash
cd c:\Users\adith\OneDrive\Desktop\wci-emailagent
python -m uvicorn start:app --reload --port 8000
```

### Frontend:
```bash
cd c:\Users\adith\OneDrive\Desktop\wci-emailagent\frontend
npm run dev
```

Visit: http://localhost:5173

---

## Key Features Implemented

✅ Multi-user OAuth authentication (existing)
✅ JSON file-based state management
✅ Missing fields validation
✅ AI follow-up email generation (Azure OpenAI)
✅ Epicor sync on mark as processed
✅ REST API with CORS support
✅ React TypeScript frontend setup
✅ Tailwind CSS styling
✅ React Query for data fetching

## Remaining Work Estimate
- 10-15 more React components
- Main App routing setup
- Environment configuration
- Testing and bug fixes

Total: ~2-3 hours of focused work
