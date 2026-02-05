
import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface AlignmentChartProps {
  score: number;
}

const AlignmentChart: React.FC<AlignmentChartProps> = ({ score }) => {
  const data = [
    { name: 'Aligned', value: score },
    { name: 'Remaining', value: 100 - score },
  ];

  const COLORS = ['#059669', '#f1f5f9']; // Emerald-600 for the main score

  return (
    <div className="w-32 h-32 relative">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={30}
            outerRadius={45}
            paddingAngle={0}
            dataKey="value"
            startAngle={90}
            endAngle={450}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex items-center justify-center flex-col">
        <span className="text-xl font-bold text-emerald-800">{score}%</span>
        <span className="text-[10px] text-emerald-500 font-bold uppercase">Aligné</span>
      </div>
    </div>
  );
};

export default AlignmentChart;
