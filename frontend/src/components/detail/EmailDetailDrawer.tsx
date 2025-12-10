import { AlertCircle, CheckCircle2, ChevronDown, Circle, Mail, Shield, X } from 'lucide-react';
import { useState } from 'react';
import { useBomImpact } from '../../hooks/useBomImpact';
import { useEmailDetail, useGenerateFollowup, useRawEmailContent, useUpdateEmailProcessed } from '../../hooks/useEmails';
import { formatDate } from '../../lib/utils';
import type { MissingField } from '../../types/email';
import { AttachmentList } from '../email/AttachmentList';
import { EmailBodyViewer } from '../email/EmailBodyViewer';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { PriceChangeBadge } from '../ui/PriceChangeBadge';
import { VerificationBadge } from '../ui/VerificationBadge';
import { BomImpactPanel } from './BomImpactPanel';
import { FollowupModal } from './FollowupModal';
import { MissingFieldsChecklist } from './MissingFieldsChecklist';
import { PriceChangeSummary } from './PriceChangeSummary';
import { ProductsTable } from './ProductsTable';
import { SupplierInfo } from './SupplierInfo';
import { WorkflowStepper } from './WorkflowStepper';

interface EmailDetailDrawerProps {
  messageId: string | null;
  onClose: () => void;
}

export function EmailDetailDrawer({ messageId, onClose }: EmailDetailDrawerProps) {
  const [showFollowupModal, setShowFollowupModal] = useState(false);
  const [followupDraft, setFollowupDraft] = useState('');
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [pendingWarnings, setPendingWarnings] = useState<string[]>([]);
  const [isEmailBodyExpanded, setIsEmailBodyExpanded] = useState(false);

  const { data, isLoading } = useEmailDetail(messageId);
  const { data: rawEmail, isLoading: isLoadingRaw } = useRawEmailContent(messageId);
  const { data: bomImpactData } = useBomImpact(messageId);
  const updateProcessed = useUpdateEmailProcessed();
  const generateFollowup = useGenerateFollowup();

  // Debug: Log is_price_change value
  console.log('EmailDetailDrawer - is_price_change:', data?.state?.is_price_change, 'data.state:', data?.state);

  if (!messageId) return null;

  // Check if all BOM impact products have been decided (approved or rejected)
  const isPriceChange = data?.state?.is_price_change;
  const verificationStatus = data?.state?.verification_status;
  const hasBomImpacts = bomImpactData?.impacts && bomImpactData.impacts.length > 0;
  const allBomImpactsDecided = hasBomImpacts
    ? bomImpactData.impacts.every((i) => i.approved || i.rejected || i.status === 'error')
    : true; // If no BOM impacts, consider it decided

  // Determine why the button might be disabled
  const isVerificationBlocking = verificationStatus === 'pending_review' || verificationStatus === 'rejected';
  const isNotPriceChange = isPriceChange === false;
  const isBomImpactBlocking = isPriceChange && hasBomImpacts && !allBomImpactsDecided;

  // Disable "Mark as Processed" when:
  // 1. Verification is pending or rejected
  // 2. Email is NOT a price change (only price change emails should be processed/synced)
  // 3. For price change emails: BOM impacts not all decided
  const canMarkAsProcessed = !isVerificationBlocking && !isNotPriceChange && !isBomImpactBlocking;

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
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-white shadow-lg z-50 overflow-y-auto">
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
                    {/* Category 1: Verification Status (MANDATORY for ALL) */}
                    {data.state.verification_status && (
                      <VerificationBadge status={data.state.verification_status} />
                    )}

                    {/* Category 2: Price Change Detection (MANDATORY for verified/approved) */}
                    {(data.state.verification_status === 'verified' || data.state.verification_status === 'manually_approved')
                      && data.state.llm_detection_performed && data.state.is_price_change !== null && (
                      <PriceChangeBadge isPriceChange={data.state.is_price_change} />
                    )}

                    {/* Category 3: Epicor Integration (MANDATORY for verified/approved + price change) */}
                    {(data.state.verification_status === 'verified' || data.state.verification_status === 'manually_approved')
                      && data.state.is_price_change === true && (
                      data.state.epicor_synced ? (
                        <Badge variant="success">Processed</Badge>
                      ) : (
                        <Badge variant="warning">Unprocessed</Badge>
                      )
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
              <div className="mt-4 flex flex-col gap-2">
                <div className="flex gap-3">
                  <Button
                    onClick={() => handleToggleProcessed()}
                    variant={data.state.processed ? 'outline' : 'default'}
                    disabled={updateProcessed.isPending || (!data.state.processed && !canMarkAsProcessed)}
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
                {/* Warning messages when button is disabled */}
                {!data.state.processed && isVerificationBlocking && (
                  <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 px-3 py-2 rounded">
                    <AlertCircle className="h-4 w-4" />
                    <span>
                      {verificationStatus === 'pending_review'
                        ? 'Email is pending vendor verification. Please verify or approve the vendor first.'
                        : 'Email was rejected during vendor verification and cannot be processed.'}
                    </span>
                  </div>
                )}
                {!data.state.processed && !isVerificationBlocking && isNotPriceChange && (
                  <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded">
                    <AlertCircle className="h-4 w-4" />
                    <span>This email is not a price change notification and does not require Epicor sync.</span>
                  </div>
                )}
                {!data.state.processed && !isVerificationBlocking && !isNotPriceChange && isBomImpactBlocking && (
                  <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 px-3 py-2 rounded">
                    <AlertCircle className="h-4 w-4" />
                    <span>Please approve or reject all products in BOM Impact Analysis before marking as processed</span>
                  </div>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-6 space-y-4">
              {/* Original Email Content - Collapsible */}
              {rawEmail && !isLoadingRaw && (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setIsEmailBodyExpanded(!isEmailBodyExpanded)}
                    className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-gray-500" />
                      <h4 className="text-sm font-medium text-gray-700">Mail</h4>
                    </div>
                    <ChevronDown
                      className={`h-4 w-4 text-gray-500 transition-transform ${
                        isEmailBodyExpanded ? 'rotate-180' : ''
                      }`}
                    />
                  </button>

                  {isEmailBodyExpanded && (
                    <div className="px-3 py-3 border-t border-gray-200 bg-white">
                      {/* Email Body */}
                      <div className="mb-3">
                        <EmailBodyViewer
                          body={rawEmail.body}
                          bodyType={rawEmail.bodyType}
                        />
                      </div>

                      {/* Attachments */}
                      {rawEmail.attachments && rawEmail.attachments.length > 0 && (
                        <div>
                          <h5 className="text-xs font-medium text-gray-600 mb-2">
                            Attachments ({rawEmail.attachments.length})
                          </h5>
                          <AttachmentList
                            attachments={rawEmail.attachments}
                            messageId={messageId}
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {isLoadingRaw && (
                <div className="border border-gray-200 rounded-lg p-3">
                  <div className="text-sm text-gray-500">Loading email content...</div>
                </div>
              )}

              <div className="border-t border-gray-200 pt-4">
                <h4 className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">Extracted Data</h4>
              </div>

              {/* Workflow Stepper - Shows 3-Stage Workflow */}
              <WorkflowStepper hasEpicorSync={!!data.epicor_status} />

              {/* Vendor Verification Status */}
              {data.state.verification_status && (
                <div className="bg-white border border-gray-200 rounded-lg p-3">
                  <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                    <Shield className="h-3.5 w-3.5 text-gray-500" />
                    Vendor Verification
                  </h4>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-600">Status:</span>
                      <VerificationBadge
                        status={data.state.verification_status}
                        method={data.state.verification_method}
                        showMethod
                      />
                    </div>

                    {data.state.vendor_info && (
                      <div className="text-xs">
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

              {/* BOM Impact Analysis - Show for price change emails */}
              {data.state.is_price_change && (
                <BomImpactPanel messageId={messageId} />
              )}

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
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h4 className="text-xs font-semibold text-gray-700 mb-3 flex items-center gap-1.5 uppercase tracking-wide">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Integration Results
                  </h4>

                  {/* Stats Grid */}
                  <div className="grid grid-cols-4 gap-2 mb-3">
                    <div className="text-center">
                      <div className="text-lg font-bold text-gray-900">{data.epicor_status.total}</div>
                      <div className="text-xs text-gray-600">Total</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-green-600">{data.epicor_status.successful}</div>
                      <div className="text-xs text-gray-600">Success</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-red-600">{data.epicor_status.failed}</div>
                      <div className="text-xs text-gray-600">Failed</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-gray-400">{data.epicor_status.skipped}</div>
                      <div className="text-xs text-gray-600">Skipped</div>
                    </div>
                  </div>

                  {/* Details */}
                  {data.epicor_status.details && data.epicor_status.details.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-medium text-gray-600 mb-2">Part Details:</div>
                      {data.epicor_status.details.map((detail, idx) => (
                        <div
                          key={idx}
                          className={`
                            text-xs p-2 rounded border
                            ${detail.status === 'success'
                              ? 'bg-white border-green-200'
                              : detail.status === 'failed'
                              ? 'bg-red-50 border-red-200'
                              : 'bg-gray-50 border-gray-200'}
                          `}
                        >
                          <div className="flex items-start justify-between mb-1">
                            <code className="font-mono font-semibold text-gray-900 text-xs">
                              {detail.part_num}
                            </code>
                            <span className={`
                              px-1.5 py-0.5 rounded text-xs font-medium
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
