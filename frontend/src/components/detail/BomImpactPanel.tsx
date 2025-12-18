import {
    AlertTriangle,
    Ban,
    CheckCircle,
    ChevronDown,
    ChevronLeft,
    ChevronRight,
    ChevronUp,
    DollarSign,
    Info,
    Layers,
    Package,
    RefreshCw,
    Shield,
    XCircle
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { useApproveAllBomImpacts, useApproveBomImpact, useBomImpact, useReanalyzeBomImpact, useRejectBomImpact } from '../../hooks/useBomImpact';
import type { BomImpactAssemblyDetail, BomImpactResult } from '../../types/email';
import { Badge } from '../ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface BomImpactPanelProps {
  messageId: string;
}

// Pagination constants
const PRODUCTS_PER_PAGE = 10;

// Format currency
const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
};

// Format percentage
const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '0.00%';
  return `${value.toFixed(2)}%`;
};

// Check if a product has been decided (approved or rejected)
const isDecided = (impact: BomImpactResult): boolean => impact.approved || impact.rejected;

// Check if a BOM impact result is verified (component AND supplier-part validated)
const isVerified = (impact: BomImpactResult): boolean => {
  return impact.component_validated && impact.supplier_part_validated;
};

// Single product BOM impact card
function ProductBomImpact({
  impact,
  onApprove,
  onReject,
  isApproving,
  isRejecting,
}: {
  impact: BomImpactResult;
  onApprove: () => void;
  onReject: () => void;
  isApproving: boolean;
  isRejecting: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const summary = impact.summary;
  const riskSummary = summary?.risk_summary;
  const decided = isDecided(impact);

  return (
    <Card className="mb-4">
      <CardHeader className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-3">
            <CardTitle className="text-base">
              {impact.part_num || `Product ${impact.product_index + 1}`}
            </CardTitle>
            <Badge variant={impact.status === 'success' ? 'success' : impact.status === 'error' ? 'danger' : 'warning'}>
              {impact.status.toUpperCase()}
            </Badge>
            {impact.approved && (
              <Badge variant="success">
                <CheckCircle className="h-3 w-3 mr-1" />
                APPROVED
              </Badge>
            )}
            {impact.rejected && (
              <Badge variant="danger">
                <Ban className="h-3 w-3 mr-1" />
                REJECTED
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!decided && impact.status !== 'error' && (
              <>
                <button
                  onClick={(e) => { e.stopPropagation(); onApprove(); }}
                  disabled={isApproving || isRejecting}
                  className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {isApproving ? 'Approving...' : 'Approve'}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onReject(); }}
                  disabled={isApproving || isRejecting}
                  className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                >
                  {isRejecting ? 'Rejecting...' : 'Reject'}
                </button>
              </>
            )}
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </div>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent>
          {/* Summary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-gray-50 p-3 rounded">
              <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
                <Layers className="h-3 w-3" />
                Assemblies
              </div>
              <div className="text-lg font-semibold">{summary?.total_assemblies_affected || 0}</div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
                <DollarSign className="h-3 w-3" />
                Annual Impact
              </div>
              <div className="text-lg font-semibold">
                {formatCurrency(impact.total_annual_cost_impact)}
                {summary?.assemblies_with_demand_data === 0 && summary?.total_assemblies_affected > 0 && (
                  <span className="text-xs text-gray-400 font-normal ml-1">(no forecast data)</span>
                )}
              </div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
                <AlertTriangle className="h-3 w-3" />
                High Risk
              </div>
              <div className="text-lg font-semibold text-red-600">
                {(riskSummary?.critical || 0) + (riskSummary?.high || 0)}
              </div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
                <Shield className="h-3 w-3" />
                Auto-Approve
              </div>
              <div className="text-lg font-semibold">
                {impact.can_auto_approve ? (
                  <span className="text-green-600">Yes</span>
                ) : (
                  <span className="text-red-600">No</span>
                )}
              </div>
            </div>
          </div>

          {/* Price Change Info */}
          <div className="mb-4 p-3 bg-blue-50 rounded">
            <div className="text-xs text-blue-600 font-medium mb-1">Price Change</div>
            <div className="flex items-center gap-4">
              <span className="text-gray-600">{formatCurrency(impact.old_price)}</span>
              <span className="text-gray-400">→</span>
              <span className="font-semibold">{formatCurrency(impact.new_price)}</span>
              <Badge variant={impact.price_delta && impact.price_delta > 0 ? 'danger' : 'success'}>
                {impact.price_delta && impact.price_delta > 0 ? '+' : ''}{formatPercent(impact.price_change_pct)}
              </Badge>
            </div>
          </div>

          {/* Validation Status */}
          <div className="mb-4 grid grid-cols-3 gap-4">
            <div className="flex items-center gap-2">
              {impact.component_validated ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
              <span className="text-sm">
                Component: {impact.component_validated ? 'Validated' : 'Not Found'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {impact.supplier_validated ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
              <span className="text-sm">
                Supplier: {impact.supplier_validated ? impact.supplier_name : 'Not Found'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {impact.supplier_part_validated ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
              <span className="text-sm" title={impact.supplier_part_validation_error || undefined}>
                Supplier-Part: {impact.supplier_part_validated ? 'Linked' : impact.supplier_part_validation_error || 'Not Linked'}
              </span>
            </div>
          </div>

          {/* Affected Assemblies Table */}
          {impact.impact_details && impact.impact_details.length > 0 ? (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Affected Assemblies</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-2 py-1 text-left">Assembly</th>
                      <th className="px-2 py-1 text-right">Qty</th>
                      <th className="px-2 py-1 text-right">Cost Increase</th>
                      <th className="px-2 py-1 text-right">Weekly Demand</th>
                      <th className="px-2 py-1 text-right">Annual Impact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {impact.impact_details.slice(0, 10).map((detail: BomImpactAssemblyDetail, idx: number) => (
                      <tr key={idx} className="border-b">
                        <td className="px-2 py-1">
                          <div className="font-medium">{detail.assembly_part_num}</div>
                          <div className="text-gray-500 truncate max-w-[200px]">{detail.assembly_description}</div>
                        </td>
                        <td className="px-2 py-1 text-right">{detail.cumulative_qty || detail.qty_per}</td>
                        <td className="px-2 py-1 text-right">
                          {formatCurrency(detail.cost_increase_per_unit)}
                        </td>
                        <td className="px-2 py-1 text-right">{detail.weekly_demand ?? 0}</td>
                        <td className="px-2 py-1 text-right">
                          {formatCurrency(detail.annual_cost_impact)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-gray-100 font-semibold">
                    <tr>
                      <td className="px-2 py-2 text-left" colSpan={3}>Total</td>
                      <td className="px-2 py-2 text-right">
                        {impact.impact_details.reduce((sum, d) => sum + (d.weekly_demand ?? 0), 0)}
                      </td>
                      <td className="px-2 py-2 text-right">{formatCurrency(impact.total_annual_cost_impact)}</td>
                    </tr>
                  </tfoot>
                </table>
                {impact.impact_details.length > 10 && (
                  <p className="text-xs text-gray-500 mt-2">
                    Showing 10 of {impact.impact_details.length} assemblies
                  </p>
                )}
              </div>
            </div>
          ) : (
            /* No parent assemblies found message */
            <div className="mt-4 p-4 bg-gray-50 rounded text-center">
              <Layers className="h-8 w-8 mx-auto mb-2 text-gray-400" />
              <p className="text-sm text-gray-600 font-medium">No Parent Assemblies Found</p>
              <p className="text-xs text-gray-500 mt-1">
                This component is not used in any BOMs, or it may be a top-level part.
              </p>
            </div>
          )}

          {/* Unified Recommendations & Data Quality Notice Box */}
          {(impact.recommendation || summary?.has_data_quality_issues) && (
            <div className="mt-4 p-3 bg-blue-50 rounded border border-blue-100">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1 space-y-3">
                  <h4 className="text-sm font-medium text-blue-800">Important Notices</h4>

                  {/* Recommendations */}
                  {impact.recommendation && (
                    <div>
                      <div className="text-xs font-medium text-blue-700 mb-1">Recommendation</div>
                      <p className="text-sm text-blue-700">{impact.recommendation}</p>
                    </div>
                  )}

                  {/* Data Quality Notices */}
                  {summary?.has_data_quality_issues && (
                    <div>
                      <div className="flex items-center gap-1 text-xs font-medium text-orange-700 mb-1">
                        <AlertTriangle className="h-3 w-3" />
                        Data Quality Notice
                      </div>
                      <ul className="text-xs text-orange-700 space-y-1 ml-4">
                        {(summary?.assemblies_with_unknown_risk || 0) > 0 && (
                          <li>• {summary.assemblies_with_unknown_risk} assemblies have missing selling price data</li>
                        )}
                        {(summary?.assemblies_without_demand_data || 0) > 0 && (
                          <li>• {summary.assemblies_without_demand_data} assemblies have no forecast demand data</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Processing Errors */}
          {impact.processing_errors && impact.processing_errors.length > 0 && (
            <div className="mt-4 p-3 bg-red-50 rounded">
              <h4 className="text-sm font-medium text-red-800 mb-2">Processing Errors</h4>
              <ul className="space-y-1">
                {impact.processing_errors.map((error, idx) => (
                  <li key={idx} className="text-xs text-red-700">{error}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

// Main BomImpactPanel component
export function BomImpactPanel({ messageId }: BomImpactPanelProps) {
  // ALL HOOKS MUST BE CALLED BEFORE ANY CONDITIONAL RETURNS
  // (React Rules of Hooks - hooks must be called in the same order every render)
  const { data, isLoading, error, refetch } = useBomImpact(messageId);
  const approveMutation = useApproveBomImpact();
  const rejectMutation = useRejectBomImpact();
  const approveAllMutation = useApproveAllBomImpacts();
  const reanalyzeMutation = useReanalyzeBomImpact();

  // Tab and pagination state - MUST be before any early returns
  const [activeTab, setActiveTab] = useState<'verified' | 'unverified'>('verified');
  const [currentPage, setCurrentPage] = useState(1);

  // Filter impacts by verification status
  const { verifiedImpacts, unverifiedImpacts } = useMemo(() => {
    if (!data?.impacts) return { verifiedImpacts: [], unverifiedImpacts: [] };

    const verified: BomImpactResult[] = [];
    const unverified: BomImpactResult[] = [];

    data.impacts.forEach((impact) => {
      if (isVerified(impact)) {
        verified.push(impact);
      } else {
        unverified.push(impact);
      }
    });

    return { verifiedImpacts: verified, unverifiedImpacts: unverified };
  }, [data]);

  // Select which impacts to display based on active tab
  const displayedImpacts = activeTab === 'verified' ? verifiedImpacts : unverifiedImpacts;

  // Calculate summary statistics based on displayed impacts
  const summaryStats = useMemo(() => {
    if (!displayedImpacts || displayedImpacts.length === 0) {
      return {
        totalProducts: 0,
        totalAssemblies: 0,
        totalAnnualImpact: 0,
        riskCounts: { critical: 0, high: 0, medium: 0, low: 0, unknown: 0 },
        successCount: 0,
        errorCount: 0,
        warningCount: 0,
      };
    }

    // Aggregate risk counts across displayed products
    const riskCounts = { critical: 0, high: 0, medium: 0, low: 0, unknown: 0 };
    let totalAssemblies = 0;
    let totalAnnualImpact = 0;

    displayedImpacts.forEach((impact) => {
      const riskSummary = impact.summary?.risk_summary;
      if (riskSummary) {
        riskCounts.critical += riskSummary.critical || 0;
        riskCounts.high += riskSummary.high || 0;
        riskCounts.medium += riskSummary.medium || 0;
        riskCounts.low += riskSummary.low || 0;
        riskCounts.unknown += riskSummary.unknown || 0;
      }
      totalAssemblies += impact.summary?.total_assemblies_affected || 0;
      totalAnnualImpact += impact.total_annual_cost_impact || 0;
    });

    return {
      totalProducts: displayedImpacts.length,
      totalAssemblies,
      totalAnnualImpact,
      riskCounts,
      successCount: displayedImpacts.filter((i) => i.status === 'success').length,
      errorCount: displayedImpacts.filter((i) => i.status === 'error').length,
      warningCount: displayedImpacts.filter((i) => i.status === 'warning').length,
    };
  }, [displayedImpacts]);

  // Debug: Log BOM impact data
  console.log('BomImpactPanel - messageId:', messageId, 'data:', data, 'isLoading:', isLoading, 'error:', error);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>BOM Impact Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
            <span className="ml-2 text-gray-500">Loading analysis...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>BOM Impact Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <XCircle className="h-8 w-8 text-red-400 mx-auto mb-2" />
            <p className="text-gray-500">Failed to load BOM impact analysis</p>
            <button
              onClick={() => refetch()}
              className="mt-2 text-sm text-blue-600 hover:underline"
            >
              Try again
            </button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.impacts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>BOM Impact Analysis</CardTitle>
            <button
              onClick={() => reanalyzeMutation.mutate(messageId)}
              disabled={reanalyzeMutation.isPending}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 flex items-center gap-1"
            >
              <RefreshCw className={`h-3 w-3 ${reanalyzeMutation.isPending ? 'animate-spin' : ''}`} />
              {reanalyzeMutation.isPending ? 'Analyzing...' : 'Run Analysis'}
            </button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-gray-500">
            <Layers className="h-8 w-8 mx-auto mb-2 text-gray-300" />
            <p>No BOM impact analysis available</p>
            <p className="text-xs mt-1">Click "Run Analysis" to analyze affected assemblies</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Check if all products have been decided (approved or rejected)
  const allDecided = data.impacts.every((i) => isDecided(i) || i.status === 'error');
  const pendingCount = data.impacts.filter((i) => !isDecided(i) && i.status !== 'error').length;
  const approvedCount = data.impacts.filter((i) => i.approved).length;
  const rejectedCount = data.impacts.filter((i) => i.rejected).length;

  // Pagination calculations based on displayed impacts
  const totalPages = Math.ceil(displayedImpacts.length / PRODUCTS_PER_PAGE);
  const startIndex = (currentPage - 1) * PRODUCTS_PER_PAGE;
  const endIndex = startIndex + PRODUCTS_PER_PAGE;
  const paginatedImpacts = displayedImpacts.slice(startIndex, endIndex);

  // Reset to page 1 if current page exceeds total pages (after tab switch or re-analysis)
  if (currentPage > totalPages && totalPages > 0) {
    setCurrentPage(1);
  }

  return (
    <div className="space-y-4">
      {/* Header with actions */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Layers className="h-5 w-5" />
          BOM Impact Analysis
          <Badge variant="info">{data.total_products} product(s)</Badge>
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => reanalyzeMutation.mutate(messageId)}
            disabled={reanalyzeMutation.isPending}
            className="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50 flex items-center gap-1.5 border border-gray-200"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${reanalyzeMutation.isPending ? 'animate-spin' : ''}`} />
            Re-analyze
          </button>
          {pendingCount > 0 && (
            <button
              onClick={() => approveAllMutation.mutate({ messageId })}
              disabled={approveAllMutation.isPending}
              className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center gap-1.5"
            >
              <CheckCircle className="h-3.5 w-3.5" />
              {approveAllMutation.isPending ? 'Approving...' : `Approve All (${pendingCount})`}
            </button>
          )}
          {allDecided && (
            <Badge variant={rejectedCount > 0 ? 'warning' : 'success'}>
              {approvedCount > 0 && (
                <span className="flex items-center">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  {approvedCount} Approved
                </span>
              )}
              {rejectedCount > 0 && (
                <span className="flex items-center ml-2">
                  <Ban className="h-3 w-3 mr-1" />
                  {rejectedCount} Rejected
                </span>
              )}
            </Badge>
          )}
        </div>
      </div>

      {/* Tabs for Verified/Unverified - cleaner design */}
      <div className="bg-gray-100 p-1 rounded-lg inline-flex">
        <button
          onClick={() => { setActiveTab('verified'); setCurrentPage(1); }}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'verified'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <span className="flex items-center gap-2">
            <CheckCircle className={`h-4 w-4 ${activeTab === 'verified' ? 'text-green-500' : 'text-gray-400'}`} />
            Verified
            <span className={`px-1.5 py-0.5 text-xs rounded-full ${
              activeTab === 'verified' ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-600'
            }`}>
              {verifiedImpacts.length}
            </span>
          </span>
        </button>
        <button
          onClick={() => { setActiveTab('unverified'); setCurrentPage(1); }}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'unverified'
              ? 'bg-white text-red-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <span className="flex items-center gap-2">
            <XCircle className={`h-4 w-4 ${activeTab === 'unverified' ? 'text-red-500' : 'text-gray-400'}`} />
            Unverified
            <span className={`px-1.5 py-0.5 text-xs rounded-full ${
              activeTab === 'unverified' ? 'bg-red-100 text-red-700' : 'bg-gray-200 text-gray-600'
            }`}>
              {unverifiedImpacts.length}
            </span>
          </span>
        </button>
      </div>

      {/* Empty state for verified tab */}
      {activeTab === 'verified' && verifiedImpacts.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-amber-400" />
          <p className="font-medium">No verified parts</p>
          <p className="text-xs mt-1">No products passed validation. Check the Unverified/Failed tab.</p>
        </div>
      )}

      {/* Empty state for unverified tab */}
      {activeTab === 'unverified' && unverifiedImpacts.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-400" />
          <p className="font-medium">All parts verified</p>
          <p className="text-xs mt-1">All products passed component and supplier-part validation.</p>
        </div>
      )}

      {/* Summary View Card - only show if there are products to display */}
      {displayedImpacts.length > 0 && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* Products & Assemblies */}
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-gray-500 text-xs font-medium mb-2">
                <Package className="h-4 w-4" />
                Products
              </div>
              <div className="text-2xl font-bold text-gray-900">{summaryStats.totalProducts}</div>
              <div className="text-xs text-gray-500 mt-1">
                {summaryStats.totalAssemblies} assemblies affected
              </div>
            </div>

            {/* Annual Impact */}
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-gray-500 text-xs font-medium mb-2">
                <DollarSign className="h-4 w-4" />
                Annual Impact
              </div>
              <div className="text-2xl font-bold text-blue-600">{formatCurrency(summaryStats.totalAnnualImpact)}</div>
              <div className="text-xs text-gray-500 mt-1">estimated cost</div>
            </div>

            {/* Risk */}
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-gray-500 text-xs font-medium mb-2">
                <AlertTriangle className="h-4 w-4" />
                Risk Level
              </div>
              <div className="flex items-baseline gap-3">
                <span className="text-2xl font-bold text-red-600">
                  {summaryStats.riskCounts.critical + summaryStats.riskCounts.high}
                </span>
                <span className="text-sm text-gray-500">high</span>
                <span className="text-lg font-semibold text-yellow-600">
                  {summaryStats.riskCounts.medium + summaryStats.riskCounts.low}
                </span>
                <span className="text-sm text-gray-500">low</span>
              </div>
            </div>

            {/* Status */}
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-gray-500 text-xs font-medium mb-2">
                <CheckCircle className="h-4 w-4" />
                Approval Status
              </div>
              <div className="text-2xl font-bold text-green-600">
                {displayedImpacts.filter(i => i.approved).length}/{summaryStats.totalProducts}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {displayedImpacts.filter(i => !isDecided(i) && i.status !== 'error').length > 0
                  ? `${displayedImpacts.filter(i => !isDecided(i) && i.status !== 'error').length} pending approval`
                  : 'all decided'}
              </div>
            </div>
          </div>

          {/* Pagination Info & Controls (Top) */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between bg-gray-50 px-4 py-2 rounded-lg">
              <span className="text-sm text-gray-600">
                Showing {startIndex + 1}-{Math.min(endIndex, displayedImpacts.length)} of {displayedImpacts.length} products
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-1 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <span className="text-sm font-medium">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-1 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Next page"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          )}

          {/* Product impact cards (paginated) */}
          {paginatedImpacts.map((impact) => (
            <ProductBomImpact
              key={impact.id}
              impact={impact}
              onApprove={() => approveMutation.mutate({ messageId, productIndex: impact.product_index })}
              onReject={() => rejectMutation.mutate({ messageId, productIndex: impact.product_index })}
              isApproving={approveMutation.isPending}
              isRejecting={rejectMutation.isPending}
            />
          ))}

          {/* Pagination Controls (Bottom) */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 py-4">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                First
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
              >
                <ChevronLeft className="h-3 w-3" /> Previous
              </button>

              {/* Page number buttons */}
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  // Show pages around current page
                  let pageNum: number;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-1 text-xs rounded ${
                        currentPage === pageNum
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
              >
                Next <ChevronRight className="h-3 w-3" />
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Last
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
