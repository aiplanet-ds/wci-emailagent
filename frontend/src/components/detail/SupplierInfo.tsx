import { Building2, ChevronDown, ChevronUp, Mail, Phone, User } from 'lucide-react';
import { useState } from 'react';
import type { SupplierInfo as SupplierInfoType } from '../../types/email';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface SupplierInfoProps {
  supplier: SupplierInfoType;
}

export function SupplierInfo({ supplier }: SupplierInfoProps) {
  const [expanded, setExpanded] = useState(false);

  const fields = [
    { icon: Building2, label: 'Supplier ID', value: supplier.supplier_id },
    { icon: User, label: 'Contact Person', value: supplier.contact_person },
    { icon: Mail, label: 'Email', value: supplier.contact_email },
    { icon: Phone, label: 'Phone', value: supplier.contact_phone },
  ];

  return (
    <Card>
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-gray-500" />
            <CardTitle className="text-base">
              {supplier.supplier_name || 'Supplier Information'}
            </CardTitle>
          </div>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          )}
        </div>
      </CardHeader>
      {expanded && (
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
      )}
    </Card>
  );
}
