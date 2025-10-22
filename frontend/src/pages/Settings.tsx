import { Settings as SettingsIcon, Shield, Database } from 'lucide-react';
import { VendorCacheStatus } from '../components/vendor/VendorCacheStatus';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

export function Settings() {
  // Configuration values (these would ideally come from an API endpoint)
  const config = {
    verificationEnabled: true,
    domainMatchingEnabled: true,
    cacheTTL: 24,
  };

  return (
    <div className="px-6 py-6 space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <SettingsIcon className="h-8 w-8 text-gray-700" />
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
            <p className="text-sm text-gray-600 mt-1">
              Manage vendor verification and system configuration
            </p>
          </div>
        </div>
      </div>

      {/* Vendor Verification Section */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Vendor Verification</h3>
        </div>

        {/* Configuration Card */}
        <Card className="p-6">
          <h4 className="font-medium text-gray-900 mb-4">Current Configuration</h4>

          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b border-gray-200">
              <div>
                <p className="font-medium text-gray-900">Vendor Verification</p>
                <p className="text-sm text-gray-500">
                  Verify emails against Epicor vendor list before AI extraction
                </p>
              </div>
              <Badge variant={config.verificationEnabled ? 'success' : 'default'}>
                {config.verificationEnabled ? '✅ Enabled' : '❌ Disabled'}
              </Badge>
            </div>

            <div className="flex items-center justify-between py-3 border-b border-gray-200">
              <div>
                <p className="font-medium text-gray-900">Domain Matching</p>
                <p className="text-sm text-gray-500">
                  Accept emails from any address at verified vendor domains
                </p>
              </div>
              <Badge variant={config.domainMatchingEnabled ? 'success' : 'default'}>
                {config.domainMatchingEnabled ? '✅ Enabled' : '❌ Disabled'}
              </Badge>
            </div>

            <div className="flex items-center justify-between py-3">
              <div>
                <p className="font-medium text-gray-900">Cache TTL</p>
                <p className="text-sm text-gray-500">
                  How often vendor cache refreshes automatically
                </p>
              </div>
              <Badge variant="info">{config.cacheTTL} hours</Badge>
            </div>
          </div>

          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-sm text-blue-800">
              💡 <strong>Note:</strong> To modify these settings, update the <code className="bg-blue-100 px-1 rounded">.env</code> file
              and restart the application.
            </p>
          </div>
        </Card>

        {/* Vendor Cache Status */}
        <div className="flex items-center gap-2 mt-6">
          <Database className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Vendor Cache</h3>
        </div>

        <VendorCacheStatus />
      </div>

      {/* Token Savings Info */}
      <Card className="p-6 bg-gradient-to-r from-green-50 to-blue-50 border-green-200">
        <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
          💰 Token Savings Impact
        </h4>
        <p className="text-sm text-gray-700 mb-3">
          Vendor verification helps reduce AI costs by preventing extraction on emails from
          unverified senders.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="bg-white bg-opacity-70 rounded-lg p-3">
            <p className="text-gray-600 mb-1">Scenario</p>
            <p className="font-semibold text-gray-900">1,000 emails/month</p>
          </div>
          <div className="bg-white bg-opacity-70 rounded-lg p-3">
            <p className="text-gray-600 mb-1">If 30% unverified</p>
            <p className="font-semibold text-green-700">300 emails saved</p>
          </div>
          <div className="bg-white bg-opacity-70 rounded-lg p-3">
            <p className="text-gray-600 mb-1">Estimated savings</p>
            <p className="font-semibold text-green-700">$6/month</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
