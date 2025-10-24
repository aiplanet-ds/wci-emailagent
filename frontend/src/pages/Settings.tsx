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
        </Card>

        {/* Vendor Cache Status */}
        <div className="flex items-center gap-2 mt-6">
          <Database className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Vendor Cache</h3>
        </div>

        <VendorCacheStatus />
      </div>
    </div>
  );
}
