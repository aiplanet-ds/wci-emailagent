import { useState, useMemo } from 'react';
import {
  Mail,
  CheckCircle,
  Clock,
  AlertCircle,
  TrendingUp,
  Database,
  XCircle,
  RefreshCw
} from 'lucide-react';
import { StatsCard } from '../components/dashboard/StatsCard';
import { DateRangeFilter } from '../components/dashboard/DateRangeFilter';
import { ProcessingChart } from '../components/dashboard/ProcessingChart';
import { useDashboardStats } from '../hooks/useDashboard';
import type { DateRangeOption } from '../types/dashboard';

export function Dashboard() {
  const [dateRange, setDateRange] = useState<DateRangeOption>('all');

  // Calculate date range for API call
  const { startDate, endDate } = useMemo(() => {
    const now = new Date();
    let start: string | undefined;
    let end: string | undefined;

    switch (dateRange) {
      case 'today':
        start = new Date(now.setHours(0, 0, 0, 0)).toISOString();
        end = new Date(now.setHours(23, 59, 59, 999)).toISOString();
        break;
      case 'last7days':
        start = new Date(now.setDate(now.getDate() - 7)).toISOString();
        end = new Date().toISOString();
        break;
      case 'last30days':
        start = new Date(now.setDate(now.getDate() - 30)).toISOString();
        end = new Date().toISOString();
        break;
      case 'all':
      default:
        start = undefined;
        end = undefined;
    }

    return { startDate: start, endDate: end };
  }, [dateRange]);

  const { data: stats, isLoading, error } = useDashboardStats(startDate, endDate);

  if (isLoading) {
    return (
      <div className="px-6 py-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-6 py-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-red-500">Error loading dashboard. Please try again.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-sm text-gray-600 mt-1">
            Overview of email processing statistics
          </p>
        </div>
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Emails"
          value={stats?.total_emails || 0}
          icon={Mail}
          subtitle="Received in selected period"
          iconColor="text-blue-600"
          iconBgColor="bg-blue-100"
        />

        <StatsCard
          title="Processed"
          value={stats?.processed_count || 0}
          icon={CheckCircle}
          subtitle={`${stats?.processing_rate || 0}% of total`}
          iconColor="text-green-600"
          iconBgColor="bg-green-100"
        />

        <StatsCard
          title="Unprocessed"
          value={stats?.unprocessed_count || 0}
          icon={Clock}
          subtitle={`${stats?.unprocessed_percentage || 0}% remaining`}
          iconColor="text-amber-600"
          iconBgColor="bg-amber-100"
        />

        <StatsCard
          title="Need Follow-up"
          value={stats?.needs_followup_count || 0}
          icon={AlertCircle}
          subtitle={`${stats?.followup_percentage || 0}% of total`}
          iconColor="text-red-600"
          iconBgColor="bg-red-100"
        />
      </div>

      {/* Charts and Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Processing Status Chart */}
        <ProcessingChart
          processedCount={stats?.processed_count || 0}
          unprocessedCount={stats?.unprocessed_count || 0}
        />

        {/* Epicor Sync Status */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Epicor Sync Status</h3>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
              <div className="flex items-center gap-3">
                <Database className="h-5 w-5 text-green-600" />
                <span className="font-medium text-green-900">Successful Syncs</span>
              </div>
              <span className="text-2xl font-bold text-green-900">
                {stats?.epicor_sync_success || 0}
              </span>
            </div>

            <div className="flex items-center justify-between p-4 bg-red-50 rounded-lg">
              <div className="flex items-center gap-3">
                <XCircle className="h-5 w-5 text-red-600" />
                <span className="font-medium text-red-900">Failed Syncs</span>
              </div>
              <span className="text-2xl font-bold text-red-900">
                {stats?.epicor_sync_failed || 0}
              </span>
            </div>

            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <RefreshCw className="h-5 w-5 text-gray-600" />
                <span className="font-medium text-gray-900">Pending Syncs</span>
              </div>
              <span className="text-2xl font-bold text-gray-900">
                {stats?.epicor_sync_pending || 0}
              </span>
            </div>

            <div className="mt-4 p-4 bg-blue-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-blue-900">Success Rate</span>
                <span className="text-xl font-bold text-blue-900">
                  {stats?.epicor_success_rate || 0}%
                </span>
              </div>
              <div className="mt-2 w-full bg-blue-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${stats?.epicor_success_rate || 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Email Classification */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Email Classification</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-indigo-50 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="h-5 w-5 text-indigo-600" />
              <span className="font-medium text-indigo-900">Price Change</span>
            </div>
            <p className="text-3xl font-bold text-indigo-900">
              {stats?.price_change_count || 0}
            </p>
          </div>

          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <Mail className="h-5 w-5 text-gray-600" />
              <span className="font-medium text-gray-900">Non-Price Change</span>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {stats?.non_price_change_count || 0}
            </p>
          </div>

          <div className="p-4 bg-orange-50 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <AlertCircle className="h-5 w-5 text-orange-600" />
              <span className="font-medium text-orange-900">Missing Fields</span>
            </div>
            <p className="text-3xl font-bold text-orange-900">
              {stats?.emails_with_missing_fields || 0}
            </p>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      {stats?.recent_activity && stats.recent_activity.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>

          <div className="space-y-3">
            {stats.recent_activity.map((activity) => (
              <div
                key={activity.message_id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex-1">
                  <p className="font-medium text-gray-900 text-sm">{activity.subject}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Processed by {activity.processed_by || 'Unknown'}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">
                    {new Date(activity.processed_at).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
