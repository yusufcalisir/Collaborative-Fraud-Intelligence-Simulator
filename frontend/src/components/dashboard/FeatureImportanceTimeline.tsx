import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import type { TrainingRound } from '../../api/types';

interface FeatureImportanceTimelineProps {
  rounds: TrainingRound[];
  totalRounds?: number;
}

export default function FeatureImportanceTimeline({ rounds, totalRounds }: FeatureImportanceTimelineProps) {
  const hasData = rounds && rounds.length > 0 && rounds.some(r => r.feature_importance && Object.keys(r.feature_importance).length > 0);
  const total = totalRounds ?? 10;

  // We want to visualize these top 5 features
  const featuredKeys = [
    { key: 'amount', name: 'Transaction Amount', color: '#6366f1' },
    { key: 'merchant_risk', name: 'Merchant Risk', color: '#14b8a6' },
    { key: 'velocity', name: 'Velocity', color: '#f43f5e' },
    { key: 'country_code', name: 'Country Risk', color: '#f59e0b' },
    { key: 'account_age_days', name: 'Account Age', color: '#8b5cf6' },
  ];

  const placeholderData = Array.from({ length: total }, (_, i) => ({
    round: i + 1,
    ...featuredKeys.reduce((acc, f) => ({ ...acc, [f.key]: null as number | null }), {}),
  }));

  const data = placeholderData.map((placeholder) => {
    const actual = (rounds ?? []).find((r) => r.round_number === placeholder.round);
    if (actual && actual.feature_importance && Object.keys(actual.feature_importance).length > 0) {
      const row: Record<string, any> = { round: actual.round_number };
      featuredKeys.forEach((f) => {
        const val = actual.feature_importance?.[f.key] ?? actual.feature_importance?.[f.key.toLowerCase()] ?? 0;
        row[f.key] = parseFloat(val.toFixed(4));
      });
      return row;
    }
    return placeholder;
  });

  return (
    <div className="glass-card p-5 min-h-[420px] lg:h-[430px] flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Feature Importance Timeline
          </h3>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
            Real-time attribution convergence calculated via Integrated Gradients (IG)
          </p>
        </div>
        <div className="flex gap-2">
          <span
            className="text-[9px] px-2 py-0.5 rounded-full font-medium animate-pulse"
            style={{
              background: 'color-mix(in srgb, var(--color-accent-teal) 15%, transparent)',
              color: 'var(--color-accent-teal)',
            }}
          >
            Integrated Gradients
          </span>
          {!hasData && (
            <span className="text-[9px] px-2 py-0.5 rounded bg-[var(--color-status-warning)]/15 text-[var(--color-status-warning)] font-medium animate-pulse">
              Waiting for Round 1...
            </span>
          )}
        </div>
      </div>

      <div className="h-56 relative flex-1 min-h-0 my-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" />
            <XAxis
              dataKey="round"
              tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
              axisLine={{ stroke: 'var(--color-border)' }}
            />
            <YAxis
              tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
              axisLine={{ stroke: 'var(--color-border)' }}
              domain={[0, 1]}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--color-bg-card)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                fontSize: '11px',
                color: 'var(--color-text-primary)',
              }}
              labelFormatter={(label) => `Round ${label}`}
            />
            <Legend
              iconSize={8}
              wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }}
            />
            {featuredKeys.map((f) => (
              <Line
                key={f.key}
                type="monotone"
                dataKey={f.key}
                name={f.name}
                stroke={f.color}
                strokeWidth={1.8}
                dot={{ r: 2 }}
                activeDot={{ r: 4 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Explanation Box */}
      <div className="p-3.5 rounded-lg bg-[var(--color-accent-indigo)]/5 border border-[var(--color-accent-indigo)]/10">
        <p className="text-[10px] text-[var(--color-text-muted)] leading-relaxed">
          <strong>Explainable AI (XAI):</strong> Integrated Gradients calculates model attributions by integrating the gradients along a path from an all-zero baseline to the input transaction vector. The timeline shows how the federated global model converges on its top features round-by-round as it aggregates cross-bank patterns.
        </p>
      </div>
    </div>
  );
}
