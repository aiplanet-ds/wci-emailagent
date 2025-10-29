import React from 'react';
import { FileText, File, FileSpreadsheet, Image, Download } from 'lucide-react';

interface Attachment {
  id: string;
  name: string;
  contentType: string;
  size: number;
}

interface AttachmentListProps {
  attachments: Attachment[];
  messageId: string;
  onDownload?: (attachmentId: string, filename: string) => void;
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

const getFileIcon = (contentType: string, filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase();

  // Check by content type first
  if (contentType.startsWith('image/')) {
    return <Image className="w-5 h-5 text-purple-600" />;
  }
  if (contentType.includes('spreadsheet') || ext === 'xlsx' || ext === 'xls' || ext === 'csv') {
    return <FileSpreadsheet className="w-5 h-5 text-green-600" />;
  }
  if (contentType.includes('pdf') || ext === 'pdf') {
    return <FileText className="w-5 h-5 text-red-600" />;
  }
  if (contentType.includes('word') || ext === 'docx' || ext === 'doc') {
    return <FileText className="w-5 h-5 text-blue-600" />;
  }

  return <File className="w-5 h-5 text-gray-600" />;
};

export const AttachmentList: React.FC<AttachmentListProps> = ({
  attachments,
  messageId,
  onDownload
}) => {
  const handleDownload = (attachment: Attachment) => {
    if (onDownload) {
      onDownload(attachment.id, attachment.name);
    } else {
      // Default download behavior
      const downloadUrl = `/api/emails/${messageId}/attachments/${attachment.id}`;
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = attachment.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  if (!attachments || attachments.length === 0) {
    return (
      <div className="text-gray-500 italic text-sm">
        No attachments
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {attachments.map((attachment) => (
        <div
          key={attachment.id}
          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {getFileIcon(attachment.contentType, attachment.name)}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {attachment.name}
              </p>
              <p className="text-xs text-gray-500">
                {formatFileSize(attachment.size)}
              </p>
            </div>
          </div>
          <button
            onClick={() => handleDownload(attachment)}
            className="ml-3 p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
            title="Download attachment"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
};
