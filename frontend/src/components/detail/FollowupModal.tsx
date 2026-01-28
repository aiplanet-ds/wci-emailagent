import { Send, X, Plus, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { useSendFollowup } from '../../hooks/useEmails';

interface FollowupModalProps {
  open: boolean;
  onClose: () => void;
  followupDraft: string;
  messageId: string;
  originalSender: string;
  originalSubject: string;
}

export function FollowupModal({
  open,
  onClose,
  followupDraft,
  messageId,
  originalSender,
  originalSubject
}: FollowupModalProps) {
  // Form state
  const [toRecipients, setToRecipients] = useState<string[]>([]);
  const [ccRecipients, setCcRecipients] = useState<string[]>([]);
  const [subject, setSubject] = useState('');
  const [bodyContent, setBodyContent] = useState('');
  const [newToEmail, setNewToEmail] = useState('');
  const [newCcEmail, setNewCcEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const sendFollowup = useSendFollowup();

  // Initialize form when modal opens or draft changes
  useEffect(() => {
    if (open) {
      setToRecipients([originalSender]);
      setCcRecipients([]);
      setSubject(originalSubject.startsWith('Re:') ? originalSubject : `Re: ${originalSubject}`);
      setBodyContent(followupDraft);
      setError(null);
      setNewToEmail('');
      setNewCcEmail('');
      setShowSuccess(false);
    }
  }, [open, followupDraft, originalSender, originalSubject]);

  const handleAddToRecipient = () => {
    const email = newToEmail.trim();
    if (email && !toRecipients.includes(email) && isValidEmail(email)) {
      setToRecipients([...toRecipients, email]);
      setNewToEmail('');
    }
  };

  const handleAddCcRecipient = () => {
    const email = newCcEmail.trim();
    if (email && !ccRecipients.includes(email) && isValidEmail(email)) {
      setCcRecipients([...ccRecipients, email]);
      setNewCcEmail('');
    }
  };

  const handleRemoveToRecipient = (email: string) => {
    setToRecipients(toRecipients.filter(e => e !== email));
  };

  const handleRemoveCcRecipient = (email: string) => {
    setCcRecipients(ccRecipients.filter(e => e !== email));
  };

  const isValidEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const convertToHtml = (text: string): string => {
    // Convert plain text to HTML with proper formatting
    return text
      .split('\n')
      .map(line => `<p>${line || '&nbsp;'}</p>`)
      .join('');
  };

  const handleSend = async () => {
    // Validation
    if (toRecipients.length === 0) {
      setError('At least one recipient is required');
      return;
    }

    if (!subject.trim()) {
      setError('Subject is required');
      return;
    }

    if (!bodyContent.trim()) {
      setError('Email body is required');
      return;
    }

    setError(null);

    try {
      await sendFollowup.mutateAsync({
        messageId,
        request: {
          to_recipients: toRecipients,
          cc_recipients: ccRecipients.length > 0 ? ccRecipients : undefined,
          subject: subject.trim(),
          body_html: convertToHtml(bodyContent),
        },
      });

      // Show success message
      setShowSuccess(true);

      // Close modal after a brief delay to show success
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send email. Please try again.');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, addFn: () => void) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addFn();
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Send Follow-up Email"
      description="Review and edit the email before sending"
    >
      {/* Success State */}
      {showSuccess ? (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
            <CheckCircle2 className="h-10 w-10 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Email Sent Successfully!</h3>
          <p className="text-sm text-gray-600">Your follow-up email has been sent to the recipient.</p>
        </div>
      ) : (
      <div className="space-y-4">
        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* To Recipients */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
          <div className="border border-gray-300 rounded-lg p-2 bg-white">
            <div className="flex flex-wrap gap-1 mb-2">
              {toRecipients.map((email) => (
                <span
                  key={email}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                >
                  {email}
                  <button
                    type="button"
                    onClick={() => handleRemoveToRecipient(email)}
                    className="hover:bg-blue-200 rounded-full p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="email"
                value={newToEmail}
                onChange={(e) => setNewToEmail(e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, handleAddToRecipient)}
                placeholder="Add recipient email..."
                className="flex-1 text-sm border-0 focus:ring-0 p-0 placeholder-gray-400"
              />
              <button
                type="button"
                onClick={handleAddToRecipient}
                disabled={!newToEmail.trim() || !isValidEmail(newToEmail.trim())}
                className="text-blue-600 hover:text-blue-700 disabled:text-gray-300"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* CC Recipients */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">CC (Optional)</label>
          <div className="border border-gray-300 rounded-lg p-2 bg-white">
            <div className="flex flex-wrap gap-1 mb-2">
              {ccRecipients.map((email) => (
                <span
                  key={email}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-800 text-sm rounded-full"
                >
                  {email}
                  <button
                    type="button"
                    onClick={() => handleRemoveCcRecipient(email)}
                    className="hover:bg-gray-200 rounded-full p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="email"
                value={newCcEmail}
                onChange={(e) => setNewCcEmail(e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, handleAddCcRecipient)}
                placeholder="Add CC email..."
                className="flex-1 text-sm border-0 focus:ring-0 p-0 placeholder-gray-400"
              />
              <button
                type="button"
                onClick={handleAddCcRecipient}
                disabled={!newCcEmail.trim() || !isValidEmail(newCcEmail.trim())}
                className="text-blue-600 hover:text-blue-700 disabled:text-gray-300"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Subject */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Email Body */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
          <textarea
            value={bodyContent}
            onChange={(e) => setBodyContent(e.target.value)}
            rows={12}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-sans focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            placeholder="Enter your message..."
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end pt-2 border-t border-gray-200">
          <Button variant="outline" onClick={onClose} disabled={sendFollowup.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSend}
            disabled={sendFollowup.isPending || toRecipients.length === 0}
          >
            {sendFollowup.isPending ? (
              <>
                <span className="animate-spin mr-2">&#9696;</span>
                Sending...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Send Email
              </>
            )}
          </Button>
        </div>
      </div>
      )}
    </Modal>
  );
}
