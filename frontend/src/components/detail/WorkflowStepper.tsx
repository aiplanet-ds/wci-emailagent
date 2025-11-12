import { Mail, Bot, Database, Check } from 'lucide-react';

interface WorkflowStep {
  id: number;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
}

interface WorkflowStepperProps {
  hasEpicorSync: boolean;
}

export function WorkflowStepper({ hasEpicorSync }: WorkflowStepperProps) {
  const steps: WorkflowStep[] = [
    {
      id: 1,
      name: 'Email Detection',
      description: 'Content extracted',
      icon: Mail,
      color: 'text-blue-600',
    },
    {
      id: 2,
      name: 'AI Extraction',
      description: 'Data extracted',
      icon: Bot,
      color: 'text-purple-600',
    },
    {
      id: 3,
      name: 'Epicor Integration',
      description: hasEpicorSync ? 'Sync complete' : 'Pending sync',
      icon: Database,
      color: hasEpicorSync ? 'text-green-600' : 'text-gray-400',
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
                    step.id <= 2 || (step.id === 3 && hasEpicorSync)
                      ? 'bg-white border-green-500'
                      : 'bg-gray-50 border-gray-300'
                  }
                `}
              >
                {step.id <= 2 || (step.id === 3 && hasEpicorSync) ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <step.icon className={`h-4 w-4 ${step.color}`} />
                )}
              </div>

              <div className="mt-2 text-center">
                <div
                  className={`
                    text-xs font-medium
                    ${
                      step.id <= 2 || (step.id === 3 && hasEpicorSync)
                        ? 'text-gray-900'
                        : 'text-gray-500'
                    }
                  `}
                >
                  {step.name}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{step.description}</div>
              </div>
            </div>

            {/* Connector Line */}
            {index < steps.length - 1 && (
              <div
                className={`
                  flex-1 h-px mx-3 mt-[-1.5rem]
                  ${
                    step.id < 3 || (step.id === 2 && hasEpicorSync)
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
