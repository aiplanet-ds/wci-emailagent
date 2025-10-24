import { X, Mail, CheckCircle2, Circle, Shield } from 'lucide-react';
import { useState } from 'react';
import { Badge } from '../ui/Badge';
import { VerificationBadge } from '../ui/VerificationBadge';
import { Button } from '../ui/Button';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { formatDate } from '../../lib/utils';
import { SupplierInfo } from './SupplierInfo';
import { PriceChangeSummary } from './PriceChangeSummary';
import { ProductsTable } from './ProductsTable';
import { MissingFieldsChecklist } from './MissingFieldsChecklist';
import { FollowupModal } from './FollowupModal';
import { WorkflowStepper } from './WorkflowStepper';
import { useEmailDetail, useUpdateEmailProcessed, useGenerateFollowup } from '../../hooks/useEmails';
import type { MissingField } from '../../types/email';

interface EmailDetailDrawerProps {
  messageId: string | null;
  onClose: () => void;
}

export function EmailDetailDrawer({ messageId, onClose }: EmailDetailDrawerProps) {
  const [showFollowupModal, setShowFollowupModal] = useState(false);
  const [followupDraft, setFollowupDraft] = useState('');
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [pendingWarnings, setPendingWarnings] = useState<string[]>([]);

  const { data, isLoading } = useEmailDetail(messageId);
  const updateProcessed = useUpdateEmailProcessed();
  const generateFollowup = useGenerateFollowup();

  if (!messageId) return null;

  const handleToggleProcessed = async (force = false) => {
    if (!data) return;

    try {
      const result = await updateProcessed.mutateAsync({
        messageId,
        processed: !data.state.processed,
        force,
      });

      // Check if confirmation is needed
      if (result.needs_confirmation && !force) {
        setPendingWarnings(result.warnings || []);
        setShowConfirmDialog(true);
      } else if (result.success) {
        // Success - dialog will close automatically via query invalidation
        setShowConfirmDialog(false);
        setPendingWarnings([]);
      }
    } catch (error: any) {
      const detail = error.response?.data?.detail;

      if (typeof detail === 'object' && detail.blockers) {
        // Show critical blockers
        alert(`Cannot sync to Epicor:\n\n${detail.blockers.join('\n')}`);
      } else if (typeof detail === 'string') {
        alert(detail);
      } else {
        alert('Failed to update processed status');
      }
    }
  };

  const handleConfirmWithWarnings = () => {
    // Retry with force=true
    handleToggleProcessed(true);
  };

  const handleGenerateFollowup = async (selectedFields: MissingField[]) => {
    try {
      const result = await generateFollowup.mutateAsync({
        messageId,
        request: { missing_fields: selectedFields },
      });

      setFollowupDraft(result.followup_draft);
      setShowFollowupModal(true);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate follow-up email');
    }
  };

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-white shadow-2xl z-50 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-500">Loading...</div>
          </div>
        ) : data ? (
          <>
            {/* Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 z-10">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <Mail className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    <h2 className="text-xl font-semibold text-gray-900 break-words">
                      {data.email_data.email_metadata.subject}
                    </h2>
                  </div>
                  <div className="flex flex-wrap gap-2 text-sm text-gray-600">
                    <span>From: {data.email_data.email_metadata.sender}</span>
                    <span>•</span>
                    <span>{formatDate(data.email_data.email_metadata.date)}</span>
                  </div>
                  <div className="flex gap-2 mt-3">
                    {data.validation.is_price_change && (
                      <Badge variant="info">Price Change</Badge>
                    )}
                    {data.state.processed ? (
                      <Badge variant="success">Processed</Badge>
                    ) : (
                      <Badge variant="warning">Unprocessed</Badge>
                    )}
                    {data.validation.needs_info && (
                      <Badge variant="warning">Needs Info</Badge>
                    )}
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600 ml-4 flex-shrink-0"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>

              {/* Actions */}
              <div className="mt-4 flex gap-3">
                <Button
                  onClick={() => handleToggleProcessed()}
                  variant={data.state.processed ? 'outline' : 'default'}
                  disabled={updateProcessed.isPending}
                  className="flex items-center gap-2"
                >
                  {data.state.processed ? (
                    <>
                      <Circle className="h-4 w-4" />
                      Mark as Unprocessed
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-4 w-4" />
                      {updateProcessed.isPending ? 'Processing...' : 'Mark as Processed'}
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-6 space-y-6">
              {/* Workflow Stepper - Shows 3-Stage Workflow */}
              <WorkflowStepper hasEpicorSync={!!data.epicor_status} />

              {/* Vendor Verification Status */}
              {data.state.verification_status && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <Shield className="h-4 w-4 text-blue-600" />
                    Vendor Verification
                  </h4>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Status:</span>
                      <VerificationBadge
                        status={data.state.verification_status}
                        method={data.state.verification_method}
                        showMethod
                      />
                    </div>

                    {data.state.vendor_info && (
                      <div className="text-sm">
                        <span className="text-gray-600">Vendor:</span>{' '}
                        <span className="font-medium text-gray-900">
                          {data.state.vendor_info.vendor_name} ({data.state.vendor_info.vendor_id})
                        </span>
                      </div>
                    )}

                    {data.state.manually_approved_by && (
                      <div className="text-xs text-gray-500 pt-2 border-t border-gray-200">
                        Manually approved by {data.state.manually_approved_by}
                        {data.state.manually_approved_at && (
                          <> on {formatDate(data.state.manually_approved_at)}</>
                        )}
                      </div>
                    )}

                    {data.state.flagged_reason && (
                      <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                        {data.state.flagged_reason}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Supplier Info */}
              <SupplierInfo supplier={data.email_data.supplier_info} />

              {/* Price Change Summary */}
              <PriceChangeSummary summary={data.email_data.price_change_summary} />

              {/* Products Table */}
              <ProductsTable products={data.email_data.affected_products} />

              {/* Missing Fields Checklist */}
              {data.validation.all_missing_fields.length > 0 && (
                <MissingFieldsChecklist
                  missingFields={data.validation.all_missing_fields}
                  onGenerateFollowup={handleGenerateFollowup}
                  isGenerating={generateFollowup.isPending}
                />
              )}

              {/* Epicor Integration Results */}
              {data.epicor_status && (
                <div className="space-y-4">
                  {/* Results Summary */}
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-4">
                    <h4 className="text-sm font-semibold text-green-900 mb-3 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4" />
                      Integration Results
                    </h4>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-4 gap-3 mb-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900">{data.epicor_status.total}</div>
                        <div className="text-xs text-gray-600">Total</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">{data.epicor_status.successful}</div>
                        <div className="text-xs text-gray-600">Success</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-600">{data.epicor_status.failed}</div>
                        <div className="text-xs text-gray-600">Failed</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-400">{data.epicor_status.skipped}</div>
                        <div className="text-xs text-gray-600">Skipped</div>
                      </div>
                    </div>

                    {/* Details */}
                    {data.epicor_status.details && data.epicor_status.details.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-xs font-medium text-gray-700 mb-2">Part Details:</div>
                        {data.epicor_status.details.map((detail, idx) => (
                          <div
                            key={idx}
                            className={`
                              text-xs p-3 rounded border
                              ${detail.status === 'success'
                                ? 'bg-white border-green-200'
                                : detail.status === 'failed'
                                ? 'bg-red-50 border-red-200'
                                : 'bg-gray-50 border-gray-200'}
                            `}
                          >
                            <div className="flex items-start justify-between mb-1">
                              <code className="font-mono font-semibold text-gray-900">
                                {detail.part_num}
                              </code>
                              <span className={`
                                px-2 py-0.5 rounded text-xs font-medium
                                ${detail.status === 'success'
                                  ? 'bg-green-100 text-green-700'
                                  : detail.status === 'failed'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-gray-100 text-gray-700'}
                              `}>
                                {detail.status}
                              </span>
                            </div>

                            {detail.vendor_name && (
                              <div className="text-gray-600 mb-1">
                                Vendor: <span className="font-medium">{detail.vendor_name}</span>
                              </div>
                            )}

                            {detail.list_code && (
                              <div className="text-gray-600 mb-1">
                                List: <span className="font-medium">{detail.list_code}</span>
                              </div>
                            )}

                            {detail.status === 'success' && (
                              <div className="text-gray-700 font-medium">
                                ${detail.old_price} → ${detail.new_price}
                                {detail.effective_date && (
                                  <span className="text-gray-500 ml-2">
                                    (Effective: {detail.effective_date})
                                  </span>
                                )}
                              </div>
                            )}

                            {detail.status === 'failed' && detail.message && (
                              <div className="text-red-600 mt-1">{detail.message}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-500">Email not found</div>
          </div>
        )}
      </div>

      {/* Follow-up Modal */}
      <FollowupModal
        open={showFollowupModal}
        onClose={() => setShowFollowupModal(false)}
        followupDraft={followupDraft}
      />

      {/* Confirmation Dialog for Warnings */}
      <ConfirmDialog
        open={showConfirmDialog}
        onClose={() => setShowConfirmDialog(false)}
        onConfirm={handleConfirmWithWarnings}
        title="Missing Recommended Fields"
        message="Some recommended fields are missing. Do you want to proceed with syncing to Epicor anyway?"
        warnings={pendingWarnings}
        confirmText="Yes, Proceed"
        cancelText="Cancel"
        variant="warning"
        isLoading={updateProcessed.isPending}
      />
    </>
  );
}
