import { LogOut, LayoutDashboard, Inbox, AlertTriangle, Settings } from 'lucide-react';
import { useCurrentUser } from '../../hooks/useEmails';
import { usePendingEmails } from '../../hooks/useVendorVerification';
import { Link, useLocation } from 'react-router-dom';
import { Badge } from '../ui/Badge';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { data: user } = useCurrentUser();
  const { data: pendingData } = usePendingEmails();
  const location = useLocation();

  const pendingCount = pendingData?.total || 0;

  const handleLogout = () => {
    window.location.href = import.meta.env.VITE_LOGOUT_URL;
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-3">
              <img src="/wci-logo.jpeg" alt="WCI Logo" className="h-8 w-8 object-contain" />
              <div>
                <h1 className="text-xl font-semibold text-gray-900">WCI Co-Pilot</h1>
                <p className="text-sm text-gray-500">Supplier Email Management</p>
              </div>
            </div>

            {/* Navigation Links */}
            <nav className="flex items-center gap-2">
              <Link
                to="/dashboard"
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive('/dashboard')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <LayoutDashboard className="h-4 w-4" />
                Dashboard
              </Link>
              <Link
                to="/inbox"
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive('/inbox')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Inbox className="h-4 w-4" />
                Inbox
              </Link>
              <Link
                to="/pending-verification"
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors relative ${
                  isActive('/pending-verification')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <AlertTriangle className="h-4 w-4" />
                Pending Verification
                {pendingCount > 0 && (
                  <Badge variant="warning" className="ml-1">
                    {pendingCount}
                  </Badge>
                )}
              </Link>
              <Link
                to="/settings"
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive('/settings')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Settings className="h-4 w-4" />
                Settings
              </Link>
            </nav>
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
