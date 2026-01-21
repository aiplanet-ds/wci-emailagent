import { RefreshCw, Database, Mail, Globe, Clock, AlertTriangle } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { useVendorCache, useRefreshCache } from '../../hooks/useVendorVerification';
import { formatDate } from '../../lib/utils';

export function VendorCacheStatus() {
  const { data: cache, isLoading, error } = useVendorCache();
  const refreshMutation = useRefreshCache();

  const handleRefresh = () => {
    refreshMutation.mutate();
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="text-center text-gray-500">Loading vendor cache status...</div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center text-red-500">Error loading vendor cache status</div>
      </Card>
    );
  }

  if (!cache) {
    return null;
  }

  return (
    <Card className="p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Database className="h-5 w-5 text-blue-600" />
            Vendor Cache Status
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Verified vendor emails from Epicor
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={refreshMutation.isPending}
          className="flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? 'animate-spin' : ''}`} />
          {refreshMutation.isPending ? 'Refreshing...' : 'Refresh Cache'}
        </Button>
      </div>

      {/* Status Indicator */}
      <div className="mb-6">
        {cache.is_stale ? (
          <Badge variant="warning" className="flex items-center gap-1 w-fit">
            <AlertTriangle className="h-3 w-3" />
            Cache is stale - refresh recommended
          </Badge>
        ) : (
          <Badge variant="success" className="flex items-center gap-1 w-fit">
            <Clock className="h-3 w-3" />
            Cache is up to date
          </Badge>
        )}
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
            <Database className="h-4 w-4" />
            Vendors
          </div>
          <div className="text-2xl font-bold text-gray-900">{cache.vendor_count}</div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
            <Mail className="h-4 w-4" />
            Verified Emails
          </div>
          <div className="text-2xl font-bold text-gray-900">{cache.email_count}</div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
            <Globe className="h-4 w-4" />
            Verified Domains
          </div>
          <div className="text-2xl font-bold text-gray-900">{cache.domain_count}</div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
            <Clock className="h-4 w-4" />
            TTL (Hours)
          </div>
          <div className="text-2xl font-bold text-gray-900">{cache.ttl_hours}</div>
        </div>
      </div>

      {/* Cache Details */}
      <div className="space-y-3 text-sm">
        <div className="flex justify-between items-center">
          <span className="text-gray-600">Last Updated:</span>
          <span className="font-medium text-gray-900">
            {cache.last_updated ? formatDate(cache.last_updated) : 'Never'}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-gray-600">Next Auto-Refresh:</span>
          <span className="font-medium text-gray-900">
            {cache.next_refresh ? formatDate(cache.next_refresh) : 'N/A'}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-gray-600">Domain Matching:</span>
          <Badge variant={cache.domain_matching_enabled ? 'success' : 'default'}>
            {cache.domain_matching_enabled ? 'Enabled' : 'Disabled'}
          </Badge>
        </div>
      </div>

      {/* Success Message */}
      {refreshMutation.isSuccess && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md text-sm text-green-800">
          ✅ Vendor cache refreshed successfully!
        </div>
      )}

      {/* Error Message */}
      {refreshMutation.isError && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
          <div className="font-medium">Failed to refresh vendor cache</div>
          <div className="mt-1 text-red-700">
            {(refreshMutation.error as any)?.response?.data?.detail ||
             (refreshMutation.error as Error)?.message ||
             'Please check your Epicor API credentials and try again.'}
          </div>
        </div>
      )}
    </Card>
  );
}
