import { useState } from 'react';
import { AlertCircle, Send } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import type { MissingField } from '../../types/email';

interface MissingFieldsChecklistProps {
  missingFields: MissingField[];
  onGenerateFollowup: (selectedFields: MissingField[]) => void;
  isGenerating?: boolean;
}

export function MissingFieldsChecklist({ missingFields, onGenerateFollowup, isGenerating }: MissingFieldsChecklistProps) {
  const [selectedFields, setSelectedFields] = useState<Set<string>>(new Set());

  if (missingFields.length === 0) {
    return null;
  }

  const handleToggle = (fieldKey: string) => {
    const newSelected = new Set(selectedFields);
    if (newSelected.has(fieldKey)) {
      newSelected.delete(fieldKey);
    } else {
      newSelected.add(fieldKey);
    }
    setSelectedFields(newSelected);
  };

  const handleGenerateFollowup = () => {
    const selected = missingFields.filter(f =>
      selectedFields.has(f.field + (f.product_index !== undefined ? `_${f.product_index}` : ''))
    );
    onGenerateFollowup(selected);
  };

  const requiredFields = missingFields.filter(f => f.severity !== 'recommended');
  const recommendedFields = missingFields.filter(f => f.severity === 'recommended');

  return (
    <Card className="border-yellow-200 bg-yellow-50">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2 text-yellow-900">
          <AlertCircle className="h-5 w-5" />
          Missing Information ({missingFields.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Required Fields */}
        {requiredFields.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-900 mb-2">Required Fields</p>
            <div className="space-y-2">
              {requiredFields.map((field) => {
                const fieldKey = field.field + (field.product_index !== undefined ? `_${field.product_index}` : '');
                return (
                  <label
                    key={fieldKey}
                    className="flex items-start gap-3 p-2 rounded hover:bg-white/50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedFields.has(fieldKey)}
                      onChange={() => handleToggle(fieldKey)}
                      className="mt-0.5 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{field.label}</p>
                      <p className="text-xs text-gray-600">{field.section}</p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {/* Recommended Fields */}
        {recommendedFields.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-900 mb-2">Recommended Fields</p>
            <div className="space-y-2">
              {recommendedFields.map((field) => {
                const fieldKey = field.field + (field.product_index !== undefined ? `_${field.product_index}` : '');
                return (
                  <label
                    key={fieldKey}
                    className="flex items-start gap-3 p-2 rounded hover:bg-white/50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedFields.has(fieldKey)}
                      onChange={() => handleToggle(fieldKey)}
                      className="mt-0.5 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{field.label}</p>
                      <p className="text-xs text-gray-600">{field.section}</p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {/* Generate Button */}
        <div className="pt-2">
          <Button
            onClick={handleGenerateFollowup}
            disabled={selectedFields.size === 0 || isGenerating}
            className="w-full"
          >
            <Send className="h-4 w-4 mr-2" />
            {isGenerating ? 'Generating...' : `Write AI Follow-up (${selectedFields.size} selected)`}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
