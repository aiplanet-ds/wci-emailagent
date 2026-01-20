import { Bot, Check, Database, Mail } from 'lucide-react';

interface WorkflowStep {
  id: number;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
  isComplete: boolean;
}

interface WorkflowStepperProps {
  hasEpicorSync: boolean;
  verificationStatus: string;
  llmDetectionPerformed: boolean;
}

export function WorkflowStepper({ hasEpicorSync, verificationStatus, llmDetectionPerformed }: WorkflowStepperProps) {
  // Determine which steps are complete based on actual state
  // Step 1 (Email Detection): Always complete once email is received
  const isStep1Complete = true;

  // Step 2 (AI Extraction): Only complete when email is approved AND LLM detection has been performed
  const isApproved = verificationStatus === 'verified' || verificationStatus === 'manually_approved';
  const isStep2Complete = isApproved && llmDetectionPerformed;

  // Step 3 (Epicor Integration): Only complete when synced to Epicor
  const isStep3Complete = hasEpicorSync;

  // Determine descriptions based on state
  const getStep2Description = () => {
    if (isStep2Complete) return 'Data extracted';
    if (verificationStatus === 'pending_review') return 'Pending approval';
    if (verificationStatus === 'rejected') return 'Rejected';
    if (isApproved && !llmDetectionPerformed) return 'Pending extraction';
    return 'Pending';
  };

  const steps: WorkflowStep[] = [
    {
      id: 1,
      name: 'Email Detection',
      description: 'Content extracted',
      icon: Mail,
      color: 'text-blue-600',
      isComplete: isStep1Complete,
    },
    {
      id: 2,
      name: 'AI Extraction',
      description: getStep2Description(),
      icon: Bot,
      color: 'text-purple-600',
      isComplete: isStep2Complete,
    },
    {
      id: 3,
      name: 'Epicor Integration',
      description: isStep3Complete ? 'Sync complete' : 'Pending sync',
      icon: Database,
      color: isStep3Complete ? 'text-green-600' : 'text-gray-400',
      isComplete: isStep3Complete,
    },
  ];

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h4 className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">3-Stage Workflow</h4>

      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center flex-1">
            {/* Step Circle */}
            <div className="flex flex-col items-center">
              <div
                className={`
                  flex items-center justify-center w-8 h-8 rounded-full border
                  ${
                    step.isComplete
                      ? 'bg-white border-green-500'
                      : 'bg-gray-50 border-gray-300'
                  }
                `}
              >
                {step.isComplete ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <step.icon className={`h-4 w-4 ${step.color}`} />
                )}
              </div>

              <div className="mt-2 text-center">
                <div
                  className={`
                    text-xs font-medium
                    ${step.isComplete ? 'text-gray-900' : 'text-gray-500'}
                  `}
                >
                  {step.name}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{step.description}</div>
              </div>
            </div>

            {/* Connector Line - green if both current step AND next step are complete */}
            {index < steps.length - 1 && (
              <div
                className={`
                  flex-1 h-px mx-3 mt-[-1.5rem]
                  ${
                    step.isComplete && steps[index + 1].isComplete
                      ? 'bg-green-500'
                      : 'bg-gray-300'
                  }
                `}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
