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
    <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-gray-200 rounded-lg p-6">
      <h4 className="text-sm font-semibold text-gray-700 mb-4">3-Stage Workflow</h4>

      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center flex-1">
            {/* Step Circle */}
            <div className="flex flex-col items-center">
              <div
                className={`
                  flex items-center justify-center w-12 h-12 rounded-full border-2
                  ${
                    step.id <= 2 || (step.id === 3 && hasEpicorSync)
                      ? 'bg-white border-green-500'
                      : 'bg-gray-100 border-gray-300'
                  }
                `}
              >
                {step.id <= 2 || (step.id === 3 && hasEpicorSync) ? (
                  <Check className="h-5 w-5 text-green-500" />
                ) : (
                  <step.icon className={`h-5 w-5 ${step.color}`} />
                )}
              </div>

              <div className="mt-3 text-center">
                <div
                  className={`
                    text-sm font-medium
                    ${
                      step.id <= 2 || (step.id === 3 && hasEpicorSync)
                        ? 'text-gray-900'
                        : 'text-gray-500'
                    }
                  `}
                >
                  {step.name}
                </div>
                <div className="text-xs text-gray-500 mt-1">{step.description}</div>
              </div>
            </div>

            {/* Connector Line */}
            {index < steps.length - 1 && (
              <div
                className={`
                  flex-1 h-0.5 mx-4 mt-[-2rem]
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
