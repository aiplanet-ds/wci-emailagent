import { Building2, User, Mail, Phone } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import type { SupplierInfo as SupplierInfoType } from '../../types/email';

interface SupplierInfoProps {
  supplier: SupplierInfoType;
}

export function SupplierInfo({ supplier }: SupplierInfoProps) {
  const fields = [
    { icon: Building2, label: 'Supplier ID', value: supplier.supplier_id },
    { icon: Building2, label: 'Supplier Name', value: supplier.supplier_name },
    { icon: User, label: 'Contact Person', value: supplier.contact_person },
    { icon: Mail, label: 'Email', value: supplier.contact_email },
    { icon: Phone, label: 'Phone', value: supplier.contact_phone },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Supplier Information</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {fields.map((field, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <field.icon className="h-3.5 w-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-500">{field.label}</p>
                <p className="text-sm text-gray-900 font-medium break-words">
                  {field.value || <span className="text-gray-400 italic">Not provided</span>}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
