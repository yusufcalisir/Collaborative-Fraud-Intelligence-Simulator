import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { BankResult } from '../../api/types';
import { BANK_COLORS } from '../../api/types';
import { METRIC_LABELS } from '../../utils/constants';

interface MetricsRadarProps {
  banks: BankResult[];
}

const METRICS_KEYS = ['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc'] as const;

export default function MetricsRadar({ banks }: MetricsRadarProps) {
  // Build grouped bar chart data: each metric has local + federated bars per bank
  const data = METRICS_KEYS.map((metric) => {
    const point: Record<string, string | number> = {
      metric: METRIC_LABELS[metric] ?? metric,
    };
    banks.forEach((bank) => {
      point[`${bank.id}_local`] = bank.local_metrics?.[metric] ?? 0;
      point[`${bank.id}_fed`] = bank.federated_metrics?.[metric] ?? 0;
    });
    return point;
  });

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">
        Metrics Overview — All Banks
      </h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" />
            <XAxis
              dataKey="metric"
              tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
              axisLine={{ stroke: 'var(--color-border)' }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
              axisLine={{ stroke: 'var(--color-border)' }}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--color-bg-card)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                fontSize: '11px',
                color: 'var(--color-text-primary)',
              }}
              formatter={(value: number) => [(value * 100).toFixed(1) + '%']}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            {banks.map((bank) => (
              <Bar
                key={`${bank.id}_local`}
                dataKey={`${bank.id}_local`}
                fill={BANK_COLORS[bank.id]}
                fillOpacity={0.4}
                name={`${bank.name.split(' ')[0]} Local`}
                radius={[2, 2, 0, 0]}
                barSize={8}
              />
            ))}
            {banks.map((bank) => (
              <Bar
                key={`${bank.id}_fed`}
                dataKey={`${bank.id}_fed`}
                fill={BANK_COLORS[bank.id]}
                name={`${bank.name.split(' ')[0]} Fed.`}
                radius={[2, 2, 0, 0]}
                barSize={8}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
