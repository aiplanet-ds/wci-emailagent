import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Card } from '../ui/Card';

interface ProcessingChartProps {
  processedCount: number;
  unprocessedCount: number;
}

const COLORS = {
  processed: '#10b981', // green
  unprocessed: '#f59e0b' // amber
};

export function ProcessingChart({ processedCount, unprocessedCount }: ProcessingChartProps) {
  const data = [
    { name: 'Processed', value: processedCount, color: COLORS.processed },
    { name: 'Unprocessed', value: unprocessedCount, color: COLORS.unprocessed }
  ];

  const total = processedCount + unprocessedCount;

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Status</h3>

      {total === 0 ? (
        <div className="h-64 flex items-center justify-center">
          <p className="text-gray-500">No data available</p>
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${((percent as number) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="text-center p-3 bg-green-50 rounded-lg">
          <p className="text-sm text-green-700 font-medium">Processed</p>
          <p className="text-2xl font-bold text-green-900">{processedCount}</p>
        </div>
        <div className="text-center p-3 bg-amber-50 rounded-lg">
          <p className="text-sm text-amber-700 font-medium">Unprocessed</p>
          <p className="text-2xl font-bold text-amber-900">{unprocessedCount}</p>
        </div>
      </div>
    </Card>
  );
}
