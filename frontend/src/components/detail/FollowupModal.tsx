import { Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';

interface FollowupModalProps {
  open: boolean;
  onClose: () => void;
  followupDraft: string;
}

export function FollowupModal({ open, onClose, followupDraft }: FollowupModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(followupDraft);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="AI-Generated Follow-up Email"
      description="Review and copy the generated email to send to your supplier"
    >
      <div className="space-y-4">
        {/* Email Preview */}
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 max-h-96 overflow-y-auto">
          <pre className="whitespace-pre-wrap text-sm text-gray-900 font-sans">
            {followupDraft}
          </pre>
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={handleCopy}>
            {copied ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-2" />
                Copy to Clipboard
              </>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
