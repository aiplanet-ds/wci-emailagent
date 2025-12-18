import { AlertTriangle, CheckCircle, ChevronLeft, ChevronRight, Package, TrendingDown, TrendingUp, XCircle } from 'lucide-react';
import { useMemo, useState } from 'react';
import { formatCurrency, formatPercentage } from '../../lib/utils';
import type { AffectedProduct, EmailState } from '../../types/email';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

const PRODUCTS_PER_PAGE = 10;

// Type for validation results
type ValidationResult = NonNullable<EmailState['epicor_validation_result']>;
type ProductValidation = ValidationResult['product_validations'][number];

interface ProductsTableProps {
  products: AffectedProduct[];
  validationResults?: ValidationResult | null;
}

// Helper component for verification status icons with tooltip
function VerificationStatus({ validation }: { validation: ProductValidation | null }) {
  if (!validation) {
    return null;
  }

  const { part_validated, supplier_validated, supplier_part_validated, validation_errors } = validation;

  // Build tooltip text
  const tooltipParts: string[] = [];
  tooltipParts.push(`Part: ${part_validated ? 'Verified' : 'Not Found'}`);
  tooltipParts.push(`Supplier: ${supplier_validated ? 'Verified' : 'Not Found'}`);
  tooltipParts.push(`Supplier-Part: ${supplier_part_validated ? 'Linked' : 'Not Linked'}`);

  if (validation_errors && validation_errors.length > 0) {
    tooltipParts.push(`\nErrors: ${validation_errors.join(', ')}`);
  }

  const tooltipText = tooltipParts.join(' | ');

  return (
    <div className="flex items-center gap-0.5 ml-2" title={tooltipText}>
      {part_validated ? (
        <CheckCircle className="h-3.5 w-3.5 text-green-500" />
      ) : (
        <XCircle className="h-3.5 w-3.5 text-red-500" />
      )}
      {supplier_validated ? (
        <CheckCircle className="h-3.5 w-3.5 text-green-500" />
      ) : (
        <XCircle className="h-3.5 w-3.5 text-red-500" />
      )}
      {supplier_part_validated ? (
        <CheckCircle className="h-3.5 w-3.5 text-green-500" />
      ) : (
        <XCircle className="h-3.5 w-3.5 text-red-500" />
      )}
    </div>
  );
}

export function ProductsTable({ products, validationResults }: ProductsTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [activeTab, setActiveTab] = useState<'verified' | 'unverified'>('verified');

  // Create a map of product index to validation
  const validationMap = new Map<number, ProductValidation>();
  if (validationResults?.product_validations) {
    validationResults.product_validations.forEach((pv) => {
      validationMap.set(pv.idx, pv);
    });
  }

  // Filter products by validation status
  const { verifiedProducts, unverifiedProducts } = useMemo(() => {
    if (!validationResults?.product_validations) {
      // If no validation results, show all products as verified (no filtering)
      return {
        verifiedProducts: products.map((product, idx) => ({ product, idx })),
        unverifiedProducts: [] as { product: AffectedProduct; idx: number }[]
      };
    }

    const verified: { product: AffectedProduct; idx: number }[] = [];
    const unverified: { product: AffectedProduct; idx: number }[] = [];

    products.forEach((product, idx) => {
      const validation = validationResults.product_validations.find(pv => pv.idx === idx);
      // A product is verified if BOTH part AND supplier-part are validated
      const isVerified = validation?.part_validated && validation?.supplier_part_validated;
      if (isVerified) {
        verified.push({ product, idx });
      } else {
        unverified.push({ product, idx });
      }
    });

    return { verifiedProducts: verified, unverifiedProducts: unverified };
  }, [products, validationResults]);

  // Select which products to display based on active tab
  const displayedProducts = activeTab === 'verified' ? verifiedProducts : unverifiedProducts;

  // Pagination calculations based on filtered products
  const totalPages = Math.ceil(displayedProducts.length / PRODUCTS_PER_PAGE);
  const startIndex = (currentPage - 1) * PRODUCTS_PER_PAGE;
  const endIndex = startIndex + PRODUCTS_PER_PAGE;
  const paginatedProducts = displayedProducts.slice(startIndex, endIndex);

  // Check if supplier is not verified
  const supplierNotVerified = validationResults && validationResults.summary.suppliers_validated === 0;

  if (products.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Affected Products</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4 text-gray-500">
            <Package className="h-6 w-6 mx-auto mb-2 text-gray-400" />
            <p className="text-sm">No products found</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Package className="h-4 w-4" />
          Affected Products ({products.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Supplier Not Verified Warning */}
        {supplierNotVerified && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-800">
                Supplier ID not found in Epicor
              </p>
              <p className="text-xs text-amber-700 mt-1">
                BOM impact analysis was skipped because the supplier could not be verified.
              </p>
            </div>
          </div>
        )}

        {/* Tabs for Verified/Unverified */}
        {validationResults && (
          <div className="flex border-b border-gray-200 mb-4">
            <button
              onClick={() => { setActiveTab('verified'); setCurrentPage(1); }}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'verified'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Verified ({verifiedProducts.length})
            </button>
            <button
              onClick={() => { setActiveTab('unverified'); setCurrentPage(1); }}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'unverified'
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Unverified/Failed ({unverifiedProducts.length})
            </button>
          </div>
        )}

        {/* Empty state for verified tab */}
        {activeTab === 'verified' && verifiedProducts.length === 0 && validationResults && (
          <div className="text-center py-8 text-gray-500">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-amber-400" />
            <p className="font-medium">No verified products</p>
            <p className="text-xs mt-1">No products passed validation. Check the Unverified/Failed tab.</p>
          </div>
        )}

        {/* Empty state for unverified tab */}
        {activeTab === 'unverified' && unverifiedProducts.length === 0 && validationResults && (
          <div className="text-center py-8 text-gray-500">
            <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-400" />
            <p className="font-medium">All products verified</p>
            <p className="text-xs mt-1">All products passed part and supplier-part validation.</p>
          </div>
        )}

        {/* Products Table */}
        {paginatedProducts.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-gray-200 bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Part Number</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Old Price</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">New Price</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Change</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {paginatedProducts.map(({ product, idx: originalIndex }) => {
                    const validation = validationMap.get(originalIndex) || null;
                    const isIncrease = (product.price_change_amount ?? 0) > 0;
                    const isDecrease = (product.price_change_amount ?? 0) < 0;

                    return (
                      <tr key={originalIndex} className="hover:bg-gray-50">
                        <td className="px-3 py-2">
                          <div className="font-medium text-gray-900">{product.product_name || 'Unknown Product'}</div>
                          {product.unit_of_measure && (
                            <div className="text-xs text-gray-500">Unit: {product.unit_of_measure}</div>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center">
                            <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                              {product.product_id || 'N/A'}
                            </code>
                            <VerificationStatus validation={validation} />
                          </div>
                        </td>
                        <td className="px-3 py-2 text-right text-gray-600">
                          {formatCurrency(product.old_price, product.currency)}
                        </td>
                        <td className="px-3 py-2 text-right font-medium text-gray-900">
                          {formatCurrency(product.new_price, product.currency)}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {isIncrease && <TrendingUp className="h-3.5 w-3.5 text-red-500" />}
                            {isDecrease && <TrendingDown className="h-3.5 w-3.5 text-green-500" />}
                            <span className={`font-medium ${isIncrease ? 'text-red-600' : isDecrease ? 'text-green-600' : 'text-gray-600'}`}>
                              {formatCurrency(product.price_change_amount, product.currency)}
                            </span>
                          </div>
                          {product.price_change_percentage !== null && (
                            <div className={`text-xs ${isIncrease ? 'text-red-500' : isDecrease ? 'text-green-500' : 'text-gray-500'}`}>
                              {formatPercentage(product.price_change_percentage)}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                <span className="text-sm text-gray-600">
                  Showing {startIndex + 1}-{Math.min(endIndex, displayedProducts.length)} of {displayedProducts.length} products
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
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
                    className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label="Next page"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
