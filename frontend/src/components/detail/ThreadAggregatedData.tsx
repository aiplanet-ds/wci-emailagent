import {
  Building2,
  Calendar,
  ChevronDown,
  ChevronUp,
  FileText,
  Layers,
  Mail,
  Package,
  Phone,
  TrendingDown,
  TrendingUp,
  User,
} from 'lucide-react';
import { useState } from 'react';
import { useThreadExtractedData } from '../../hooks/useEmails';
import { formatCurrency, formatDate, formatPercentage } from '../../lib/utils';
import type { AggregatedProduct, ThreadExtractedDataSource } from '../../types/email';
import { Badge } from '../ui/Badge';

interface ThreadAggregatedDataProps {
  messageId: string;
  onEmailSelect: (messageId: string) => void;
}

// Source indicator component
function SourceBadge({ source, onEmailSelect }: { source: ThreadExtractedDataSource | undefined; onEmailSelect: (messageId: string) => void }) {
  if (!source) return null;

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onEmailSelect(source.message_id);
      }}
      className="ml-2 text-xs text-blue-600 hover:text-blue-800 hover:underline"
      title={`From email received ${source.received_at ? formatDate(source.received_at) : 'Unknown'}`}
    >
      (from reply)
    </button>
  );
}

export function ThreadAggregatedData({ messageId, onEmailSelect }: ThreadAggregatedDataProps) {
  const { data, isLoading, error } = useThreadExtractedData(messageId);
  const [expanded, setExpanded] = useState(true);

  if (isLoading) {
    return (
      <div className="border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Layers className="h-4 w-4 animate-pulse" />
          <span>Loading thread data...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return null;
  }

  // Don't show if only one email or no received emails
  if (data.received_emails_count <= 1) {
    return null;
  }

  const { aggregated_supplier_info, aggregated_price_change_summary, aggregated_affected_products } = data;
  const supplierData = aggregated_supplier_info.data;
  const supplierSources = aggregated_supplier_info.sources;
  const summaryData = aggregated_price_change_summary.data;
  const summarySources = aggregated_price_change_summary.sources;

  // Check if there's any data to display
  const hasSupplierData = Object.values(supplierData).some((v) => v !== null);
  const hasSummaryData = Object.values(summaryData).some((v) => v !== null);
  const hasProducts = aggregated_affected_products.length > 0;

  if (!hasSupplierData && !hasSummaryData && !hasProducts) {
    return null;
  }

  // Get change badge variant
  const getChangeVariant = () => {
    if (summaryData.change_type === 'increase') return 'danger';
    if (summaryData.change_type === 'decrease') return 'success';
    return 'default';
  };

  return (
    <div className="border border-purple-200 rounded-lg overflow-hidden bg-purple-50">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-purple-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-purple-600" />
          <span className="text-sm font-medium text-purple-900">
            Thread Summary
          </span>
          <Badge variant="purple">
            {data.received_emails_count} received emails
          </Badge>
          {data.emails_with_extractions > 0 && (
            <span className="text-xs text-purple-600">
              ({data.emails_with_extractions} with extracted data)
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-purple-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-purple-500" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4 bg-white">
          {/* Aggregated Supplier Info */}
          {hasSupplierData && (
            <div className="pt-4">
              <h4 className="text-xs font-semibold text-gray-600 mb-2 flex items-center gap-1.5">
                <Building2 className="h-3.5 w-3.5" />
                Combined Supplier Information
              </h4>
              <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                {supplierData.supplier_name && (
                  <div className="flex items-start gap-2">
                    <Building2 className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs text-gray-500">Supplier Name</p>
                      <p className="text-sm text-gray-900 font-medium">
                        {supplierData.supplier_name}
                        <SourceBadge source={supplierSources.supplier_name} onEmailSelect={onEmailSelect} />
                      </p>
                    </div>
                  </div>
                )}
                {supplierData.supplier_id && (
                  <div className="flex items-start gap-2">
                    <FileText className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs text-gray-500">Supplier ID</p>
                      <p className="text-sm text-gray-900 font-medium">
                        {supplierData.supplier_id}
                        <SourceBadge source={supplierSources.supplier_id} onEmailSelect={onEmailSelect} />
                      </p>
                    </div>
                  </div>
                )}
                {supplierData.contact_person && (
                  <div className="flex items-start gap-2">
                    <User className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs text-gray-500">Contact Person</p>
                      <p className="text-sm text-gray-900 font-medium">
                        {supplierData.contact_person}
                        <SourceBadge source={supplierSources.contact_person} onEmailSelect={onEmailSelect} />
                      </p>
                    </div>
                  </div>
                )}
                {supplierData.contact_email && (
                  <div className="flex items-start gap-2">
                    <Mail className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs text-gray-500">Contact Email</p>
                      <p className="text-sm text-gray-900 font-medium">
                        {supplierData.contact_email}
                        <SourceBadge source={supplierSources.contact_email} onEmailSelect={onEmailSelect} />
                      </p>
                    </div>
                  </div>
                )}
                {supplierData.contact_phone && (
                  <div className="flex items-start gap-2">
                    <Phone className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs text-gray-500">Contact Phone</p>
                      <p className="text-sm text-gray-900 font-medium">
                        {supplierData.contact_phone}
                        <SourceBadge source={supplierSources.contact_phone} onEmailSelect={onEmailSelect} />
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Aggregated Price Change Summary */}
          {hasSummaryData && (
            <div>
              <h4 className="text-xs font-semibold text-gray-600 mb-2 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" />
                Combined Price Change Summary
              </h4>
              <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                {summaryData.change_type && (
                  <div className="flex items-start gap-2">
                    {summaryData.change_type === 'increase' ? (
                      <TrendingUp className="h-3.5 w-3.5 text-red-500 mt-0.5" />
                    ) : summaryData.change_type === 'decrease' ? (
                      <TrendingDown className="h-3.5 w-3.5 text-green-500 mt-0.5" />
                    ) : (
                      <FileText className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className="text-xs text-gray-500">Change Type</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant={getChangeVariant()}>
                          {summaryData.change_type.replace('_', ' ').toUpperCase()}
                        </Badge>
                        <SourceBadge source={summarySources.change_type} onEmailSelect={onEmailSelect} />
                      </div>
                    </div>
                  </div>
                )}
                {summaryData.effective_date && (
                  <div className="flex items-start gap-2">
                    <Calendar className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs text-gray-500">Effective Date</p>
                      <p className="text-sm text-gray-900 font-medium">
                        {summaryData.effective_date}
                        <SourceBadge source={summarySources.effective_date} onEmailSelect={onEmailSelect} />
                      </p>
                    </div>
                  </div>
                )}
                {summaryData.reason && (
                  <div className="flex items-start gap-2 bg-yellow-50 -mx-3 px-3 py-2 rounded">
                    <FileText className="h-3.5 w-3.5 text-yellow-600 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs text-yellow-700 font-medium">Reason for Price Change</p>
                      <p className="text-sm text-gray-900 mt-1">
                        {summaryData.reason}
                        <SourceBadge source={summarySources.reason} onEmailSelect={onEmailSelect} />
                      </p>
                    </div>
                  </div>
                )}
                {summaryData.overall_impact && (
                  <div className="flex items-start gap-2">
                    <FileText className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs text-gray-500">Overall Impact</p>
                      <p className="text-sm text-gray-900">
                        {summaryData.overall_impact}
                        <SourceBadge source={summarySources.overall_impact} onEmailSelect={onEmailSelect} />
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Aggregated Products Table */}
          {hasProducts && (
            <div>
              <h4 className="text-xs font-semibold text-gray-600 mb-2 flex items-center gap-1.5">
                <Package className="h-3.5 w-3.5" />
                Combined Affected Products ({aggregated_affected_products.length})
              </h4>
              <div className="bg-gray-50 rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b border-gray-200 bg-gray-100">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Part #</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Old</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">New</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Change</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 bg-white">
                      {aggregated_affected_products.slice(0, 10).map((product: AggregatedProduct, idx: number) => {
                        const isIncrease = (product.price_change_amount ?? 0) > 0;
                        const isDecrease = (product.price_change_amount ?? 0) < 0;

                        return (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-3 py-2">
                              <div className="font-medium text-gray-900 text-xs">
                                {product.product_name || 'Unknown'}
                              </div>
                            </td>
                            <td className="px-3 py-2">
                              <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                                {product.product_id || 'N/A'}
                              </code>
                            </td>
                            <td className="px-3 py-2 text-right text-xs text-gray-600">
                              {formatCurrency(product.old_price, product.currency)}
                            </td>
                            <td className="px-3 py-2 text-right text-xs font-medium text-gray-900">
                              {formatCurrency(product.new_price, product.currency)}
                            </td>
                            <td className="px-3 py-2 text-right">
                              <div className="flex items-center justify-end gap-1">
                                {isIncrease && <TrendingUp className="h-3 w-3 text-red-500" />}
                                {isDecrease && <TrendingDown className="h-3 w-3 text-green-500" />}
                                <span className={`text-xs font-medium ${isIncrease ? 'text-red-600' : isDecrease ? 'text-green-600' : 'text-gray-600'}`}>
                                  {product.price_change_percentage !== null && product.price_change_percentage !== undefined
                                    ? formatPercentage(product.price_change_percentage)
                                    : formatCurrency(product.price_change_amount, product.currency)}
                                </span>
                              </div>
                            </td>
                            <td className="px-3 py-2">
                              <button
                                onClick={() => onEmailSelect(product.source_message_id)}
                                className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
                                title={product.source_received_at ? `Received ${formatDate(product.source_received_at)}` : 'View source email'}
                              >
                                {product.source_received_at ? formatDate(product.source_received_at).split(',')[0] : 'View'}
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {aggregated_affected_products.length > 10 && (
                  <div className="px-3 py-2 text-xs text-gray-500 bg-gray-50 border-t border-gray-200">
                    Showing first 10 of {aggregated_affected_products.length} products
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
