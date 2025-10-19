import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import type { AdditionalDetails as AdditionalDetailsType } from '../../types/email';

interface AdditionalDetailsProps {
  details: AdditionalDetailsType;
}

export function AdditionalDetails({ details }: AdditionalDetailsProps) {
  const hasAnyDetails = details.terms_and_conditions || details.payment_terms || details.minimum_order_quantity || details.notes;

  if (!hasAnyDetails) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Additional Details</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {details.terms_and_conditions && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Terms & Conditions</p>
              <p className="text-sm text-gray-900">{details.terms_and_conditions}</p>
            </div>
          )}

          {details.payment_terms && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Payment Terms</p>
              <p className="text-sm text-gray-900">{details.payment_terms}</p>
            </div>
          )}

          {details.minimum_order_quantity && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Minimum Order Quantity</p>
              <p className="text-sm text-gray-900">{details.minimum_order_quantity}</p>
            </div>
          )}

          {details.notes && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Notes</p>
              <p className="text-sm text-gray-900">{details.notes}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
