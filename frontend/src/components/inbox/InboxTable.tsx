import { Mail, AlertCircle, CheckCircle2, Package } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { VerificationBadge } from '../ui/VerificationBadge';
import { formatDate } from '../../lib/utils';
import type { EmailListItem } from '../../types/email';

interface InboxTableProps {
  emails: EmailListItem[];
  selectedEmailId: string | null;
  onEmailSelect: (emailId: string) => void;
}

export function InboxTable({ emails, selectedEmailId, onEmailSelect }: InboxTableProps) {
  if (emails.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <Mail className="h-12 w-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-900">No emails found</h3>
        <p className="text-sm text-gray-500 mt-1">Try adjusting your filters or search query</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Subject
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Sender
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Info
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {emails.map((email) => (
            <tr
              key={email.message_id}
              onClick={() => onEmailSelect(email.message_id)}
              className={`cursor-pointer hover:bg-gray-50 transition-colors ${
                selectedEmailId === email.message_id ? 'bg-blue-50' : ''
              }`}
            >
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  <span className="text-sm font-medium text-gray-900 line-clamp-2">{email.subject}</span>
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="text-sm text-gray-900">{email.sender}</div>
                <div className="text-xs text-gray-500">{email.supplier_name}</div>
              </td>
              <td className="px-6 py-4 text-sm text-gray-500">
                {formatDate(email.date)}
              </td>
              <td className="px-6 py-4">
                <div className="flex gap-2 flex-wrap">
                  {email.verification_status && (
                    <VerificationBadge status={email.verification_status} />
                  )}
                  {email.is_price_change && (
                    <Badge variant="info">Price Change</Badge>
                  )}
                  {email.processed && (
                    <Badge variant="success">Processed</Badge>
                  )}
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  {email.needs_info && (
                    <div className="flex items-center gap-1 text-yellow-600">
                      <AlertCircle className="h-4 w-4" />
                      <span>{email.missing_fields_count} missing</span>
                    </div>
                  )}
                  {email.has_epicor_sync && (
                    <div className="flex items-center gap-1 text-green-600">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>{email.epicor_success_count} synced</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    <Package className="h-4 w-4" />
                    <span>{email.products_count} products</span>
                  </div>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
