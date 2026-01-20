import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Shield, Database, Clock, RefreshCw, Check, AlertCircle } from 'lucide-react';
import { VendorCacheStatus } from '../components/vendor/VendorCacheStatus';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { emailApi, type TimeUnit } from '../services/api';

const TIME_UNITS: { value: TimeUnit; label: string }[] = [
  { value: 'seconds', label: 'Seconds' },
  { value: 'minutes', label: 'Minutes' },
  { value: 'hours', label: 'Hours' },
  { value: 'days', label: 'Days' },
];

export function Settings() {
  // Configuration values (these would ideally come from an API endpoint)
  const config = {
    verificationEnabled: true,
    domainMatchingEnabled: true,
    cacheTTL: 24,
  };

  // Polling interval state
  const [savedValue, setSavedValue] = useState<number>(1);
  const [savedUnit, setSavedUnit] = useState<TimeUnit>('minutes');
  const [inputValue, setInputValue] = useState<string>('1');
  const [selectedUnit, setSelectedUnit] = useState<TimeUnit>('minutes');
  const [totalSeconds, setTotalSeconds] = useState<number>(60);
  const [nextRun, setNextRun] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Load polling interval on mount
  useEffect(() => {
    loadPollingInterval();
  }, []);

  const loadPollingInterval = async () => {
    setIsLoading(true);
    try {
      const data = await emailApi.getPollingInterval();
      setSavedValue(data.value);
      setSavedUnit(data.unit);
      setInputValue(data.value.toString());
      setSelectedUnit(data.unit);
      setTotalSeconds(data.total_seconds);
      setNextRun(data.next_run);
      setIsRunning(data.is_running);
    } catch (error) {
      console.error('Failed to load polling interval:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSavePollingInterval = async () => {
    const value = parseInt(inputValue, 10);

    // Validate input
    if (isNaN(value) || value <= 0) {
      setSaveStatus('error');
      setErrorMessage('Please enter a positive number');
      return;
    }

    setIsSaving(true);
    setSaveStatus('idle');
    setErrorMessage('');

    try {
      const data = await emailApi.updatePollingInterval(value, selectedUnit);
      setSavedValue(data.value);
      setSavedUnit(data.unit);
      setInputValue(data.value.toString());
      setSelectedUnit(data.unit);
      setTotalSeconds(data.total_seconds);
      setNextRun(data.next_run);
      setIsRunning(data.is_running);
      setSaveStatus('success');

      // Reset success status after 3 seconds
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error: any) {
      setSaveStatus('error');
      setErrorMessage(error.response?.data?.detail || 'Failed to update polling interval');
    } finally {
      setIsSaving(false);
    }
  };

  const formatNextRun = (isoString: string | null): string => {
    if (!isoString) return 'Not scheduled';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString();
    } catch {
      return 'Unknown';
    }
  };

  const formatTotalSeconds = (seconds: number): string => {
    if (seconds < 60) return `${seconds} seconds`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minute${seconds >= 120 ? 's' : ''}`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hour${seconds >= 7200 ? 's' : ''}`;
    return `${Math.floor(seconds / 86400)} day${seconds >= 172800 ? 's' : ''}`;
  };

  const hasChanges = parseInt(inputValue, 10) !== savedValue || selectedUnit !== savedUnit;

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

      {/* Email Monitoring Section */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Email Monitoring</h3>
        </div>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-gray-900">Polling Configuration</h4>
            <button
              onClick={loadPollingInterval}
              disabled={isLoading}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          <div className="space-y-4">
            {/* Polling Status */}
            <div className="flex items-center justify-between py-3 border-b border-gray-200">
              <div>
                <p className="font-medium text-gray-900">Service Status</p>
                <p className="text-sm text-gray-500">
                  Email polling background service
                </p>
              </div>
              <Badge variant={isRunning ? 'success' : 'warning'}>
                {isRunning ? 'Running' : 'Stopped'}
              </Badge>
            </div>

            {/* Polling Interval Input */}
            <div className="py-3 border-b border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="font-medium text-gray-900">Polling Interval</p>
                  <p className="text-sm text-gray-500">
                    How often to check for new emails (min: 10 seconds, max: 7 days)
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                <input
                  type="number"
                  min="1"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  disabled={isLoading || isSaving}
                  className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <select
                  value={selectedUnit}
                  onChange={(e) => setSelectedUnit(e.target.value as TimeUnit)}
                  disabled={isLoading || isSaving}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed bg-white"
                >
                  {TIME_UNITS.map((unit) => (
                    <option key={unit.value} value={unit.value}>
                      {unit.label}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleSavePollingInterval}
                  disabled={isLoading || isSaving || !hasChanges}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                    hasChanges
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {isSaving ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : saveStatus === 'success' ? (
                    <>
                      <Check className="h-4 w-4" />
                      Saved
                    </>
                  ) : (
                    'Save'
                  )}
                </button>
              </div>
              {saveStatus === 'error' && (
                <div className="mt-2 flex items-center gap-2 text-red-600 text-sm">
                  <AlertCircle className="h-4 w-4" />
                  {errorMessage}
                </div>
              )}
              {!isLoading && (
                <p className="mt-2 text-xs text-gray-400">
                  Current: {formatTotalSeconds(totalSeconds)}
                </p>
              )}
            </div>

            {/* Next Poll Time */}
            <div className="flex items-center justify-between py-3">
              <div>
                <p className="font-medium text-gray-900">Next Poll</p>
                <p className="text-sm text-gray-500">
                  When the next email check will occur
                </p>
              </div>
              <Badge variant="info">{formatNextRun(nextRun)}</Badge>
            </div>
          </div>
        </Card>
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
                {config.verificationEnabled ? 'Enabled' : 'Disabled'}
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
                {config.domainMatchingEnabled ? 'Enabled' : 'Disabled'}
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
