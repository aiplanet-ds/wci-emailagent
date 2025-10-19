import { CheckCircle2, Circle, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import type { EpicorWorkflowSteps } from '../../types/email';

interface EpicorWorkflowDetailsProps {
  workflowUsed: string;
  workflowSteps?: EpicorWorkflowSteps;
}

export function EpicorWorkflowDetails({ workflowUsed, workflowSteps }: EpicorWorkflowDetailsProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Parse workflow to determine steps (infer from workflow_used string if steps not provided)
  const inferredSteps = workflowSteps || inferStepsFromWorkflow(workflowUsed);

  const steps = [
    {
      id: 'A',
      name: 'Supplier Verification',
      description: 'Retrieve vendor number and verify supplier-part relationship',
      complete: inferredSteps.step_a_complete,
    },
    {
      id: 'B',
      name: 'Price List Creation',
      description: inferredSteps.step_b_path === 'created_new'
        ? 'Created new price list entry'
        : inferredSteps.step_b_path === 'updated_existing'
        ? 'Price list exists - proceeding to update'
        : 'Check if price list exists',
      complete: inferredSteps.step_b_complete,
      path: inferredSteps.step_b_path,
    },
    {
      id: 'C',
      name: 'Effective Date Management',
      description: 'Update header-level effective dates',
      complete: inferredSteps.step_c_complete,
    },
    {
      id: 'D',
      name: 'Price Update',
      description: 'Update part price (inherits dates from header)',
      complete: inferredSteps.step_d_complete,
    },
  ];

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-green-600" />
          <h5 className="text-sm font-semibold text-gray-900">
            4-Step Epicor Workflow
          </h5>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        )}
      </button>

      {/* Workflow Steps */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3">
          {steps.map((step) => (
            <div key={step.id} className="flex items-start gap-3">
              {/* Step Icon */}
              <div className="flex-shrink-0 mt-0.5">
                {step.complete ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <Circle className="h-5 w-5 text-gray-300" />
                )}
              </div>

              {/* Step Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-semibold text-gray-500">
                    Step {step.id}:
                  </span>
                  <span className={`text-sm font-medium ${step.complete ? 'text-gray-900' : 'text-gray-500'}`}>
                    {step.name}
                  </span>
                  {step.path && (
                    <span className={`
                      text-xs px-2 py-0.5 rounded-full font-medium
                      ${step.path === 'created_new'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-green-100 text-green-700'}
                    `}>
                      {step.path === 'created_new' ? 'NO → Created New' : 'YES → Updated'}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{step.description}</p>
              </div>
            </div>
          ))}

          {/* Workflow Summary */}
          <div className="mt-4 pt-3 border-t border-gray-200">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">Workflow:</span>
              <code className="bg-gray-100 px-2 py-1 rounded text-gray-700 font-mono">
                {workflowUsed}
              </code>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper function to infer workflow steps from workflow_used string
function inferStepsFromWorkflow(workflowUsed: string): EpicorWorkflowSteps {
  const isNewWorkflow = workflowUsed.includes('4-Step');
  const isCreatedNew = workflowUsed.includes('Created New Entry');

  return {
    step_a_complete: isNewWorkflow,
    step_b_complete: isNewWorkflow,
    step_b_path: isCreatedNew ? 'created_new' : isNewWorkflow ? 'updated_existing' : null,
    step_c_complete: isNewWorkflow && !isCreatedNew,
    step_d_complete: isNewWorkflow,
  };
}

// Import Database icon
import { Database } from 'lucide-react';
