import React from 'react';

interface EmailBodyViewerProps {
  body: string;
  bodyType: 'html' | 'text';
  className?: string;
}

// Basic HTML sanitization function (replace with DOMPurify later)
const sanitizeHtml = (html: string): string => {
  // This is a very basic sanitization - we'll improve with DOMPurify
  // For now, just remove script tags and event handlers
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/on\w+="[^"]*"/g, '')
    .replace(/on\w+='[^']*'/g, '');
};

export const EmailBodyViewer: React.FC<EmailBodyViewerProps> = ({
  body,
  bodyType,
  className = ''
}) => {
  const renderBody = () => {
    if (bodyType === 'html') {
      // Sanitize HTML to prevent XSS attacks
      const sanitizedHtml = sanitizeHtml(body);

      return (
        <div
          className="prose prose-sm max-w-none"
          dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
          style={{
            fontSize: '14px',
            lineHeight: '1.6',
            color: '#1f2937'
          }}
        />
      );
    }

    // Plain text - preserve formatting with line breaks
    return (
      <pre className="whitespace-pre-wrap font-sans text-sm text-gray-900 leading-relaxed">
        {body}
      </pre>
    );
  };

  if (!body || body.trim() === '') {
    return (
      <div className={`text-gray-500 italic text-sm ${className}`}>
        No email body content available
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      <div className="max-h-[500px] overflow-y-auto">
        {renderBody()}
      </div>
    </div>
  );
};
