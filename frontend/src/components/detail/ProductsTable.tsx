import { Package, TrendingDown, TrendingUp } from 'lucide-react';
import { formatCurrency, formatPercentage } from '../../lib/utils';
import type { AffectedProduct } from '../../types/email';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface ProductsTableProps {
  products: AffectedProduct[];
}

export function ProductsTable({ products }: ProductsTableProps) {
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
              {products.map((product, idx) => {
                const isIncrease = (product.price_change_amount ?? 0) > 0;
                const isDecrease = (product.price_change_amount ?? 0) < 0;

                return (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <div className="font-medium text-gray-900">{product.product_name || 'Unknown Product'}</div>
                      {product.unit_of_measure && (
                        <div className="text-xs text-gray-500">Unit: {product.unit_of_measure}</div>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {product.product_id || 'N/A'}
                      </code>
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
      </CardContent>
    </Card>
  );
}
