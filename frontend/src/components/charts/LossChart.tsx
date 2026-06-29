import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { TrainingRound } from '../../api/types';

interface LossChartProps {
  rounds: TrainingRound[];
}

export default function LossChart({ rounds }: LossChartProps) {
  const data = rounds.map((r) => ({
    round: r.round_number,
    loss: parseFloat(r.global_loss.toFixed(4)),
    participants: r.participating_banks.length,
    dropped: r.dropped_banks.length > 0,
  }));

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">
        Training Loss Convergence
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" />
            <XAxis
              dataKey="round"
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
              axisLine={{ stroke: 'var(--color-border)' }}
              label={{ value: 'Round', position: 'insideBottom', offset: -2, fill: 'var(--color-text-muted)', fontSize: 10 }}
            />
            <YAxis
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
              axisLine={{ stroke: 'var(--color-border)' }}
              label={{ value: 'Loss', angle: -90, position: 'insideLeft', fill: 'var(--color-text-muted)', fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--color-bg-card)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                fontSize: '12px',
                color: 'var(--color-text-primary)',
              }}
              formatter={(value: number) => [value.toFixed(4), 'Loss']}
              labelFormatter={(label) => `Round ${label}`}
            />
            <Legend wrapperStyle={{ fontSize: '11px', color: 'var(--color-text-muted)' }} />
            <Line
              type="monotone"
              dataKey="loss"
              stroke="var(--color-accent-indigo)"
              strokeWidth={2}
              dot={(props: Record<string, unknown>) => {
                const { cx, cy, payload } = props as { cx: number; cy: number; payload: { dropped: boolean } };
                const isDrop = payload?.dropped;
                return (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isDrop ? 5 : 3}
                    fill={isDrop ? 'var(--color-accent-rose)' : 'var(--color-accent-indigo)'}
                    stroke={isDrop ? 'var(--color-accent-rose)' : 'var(--color-accent-indigo)'}
                    strokeWidth={isDrop ? 2 : 0}
                  />
                );
              }}
              activeDot={{ r: 5, fill: 'var(--color-accent-indigo-light)' }}
              name="Global Loss"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-[var(--color-text-muted)] mt-2">
        Red dots indicate rounds with client dropout.
      </p>
    </div>
  );
}
