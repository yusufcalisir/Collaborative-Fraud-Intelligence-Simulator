import React from 'react';
import { motion } from 'framer-motion';
import type { BankResult } from '../../api/types';
import { BANK_COLORS } from '../../api/types';
import { formatPercent, formatDelta } from '../../utils/formatters';
import { METRIC_LABELS } from '../../utils/constants';

interface MetricsComparisonProps {
  banks: BankResult[];
}

const METRICS_KEYS = ['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc'] as const;

export default function MetricsComparison({ banks }: MetricsComparisonProps) {
  if (banks.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-card p-6"
    >
      <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">
        Local vs Federated - Performance Comparison
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border)]">
              <th className="text-left py-2 px-3 text-xs font-medium text-[var(--color-text-muted)]">
                Metric
              </th>
              {banks.map((bank) => (
                <th
                  key={bank.id}
                  colSpan={3}
                  className="text-center py-2 px-2 text-xs font-medium"
                  style={{ color: BANK_COLORS[bank.id] }}
                >
                  {bank.name}
                </th>
              ))}
            </tr>
            <tr className="border-b border-[var(--color-border-subtle)]">
              <th />
              {banks.map((bank) => (
                <React.Fragment key={bank.id}>
                  <th className="text-center py-1.5 px-2 text-[10px] font-medium text-[var(--color-text-muted)]">
                    Local
                  </th>
                  <th className="text-center py-1.5 px-2 text-[10px] font-medium text-[var(--color-text-muted)]">
                    Federated
                  </th>
                  <th className="text-center py-1.5 px-2 text-[10px] font-medium text-[var(--color-text-muted)]">
                    Δ
                  </th>
                </React.Fragment>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS_KEYS.map((metric) => (
              <tr
                key={metric}
                className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-card-hover)] transition-colors"
              >
                <td className="py-2.5 px-3 text-xs font-medium text-[var(--color-text-secondary)]">
                  {METRIC_LABELS[metric] ?? metric}
                </td>
                {banks.map((bank) => {
                  const local = bank.local_metrics?.[metric] ?? 0;
                  const federated = bank.federated_metrics?.[metric] ?? 0;
                  const delta = federated - local;
                  const isPositive = delta > 0.001;
                  const isNegative = delta < -0.001;

                  return (
                    <React.Fragment key={bank.id}>
                      <td className="text-center py-2.5 px-2 font-mono text-xs text-[var(--color-text-secondary)]">
                        {formatPercent(local)}
                      </td>
                      <td className="text-center py-2.5 px-2 font-mono text-xs text-[var(--color-text-primary)] font-medium">
                        {formatPercent(federated)}
                      </td>
                      <td className="text-center py-2.5 px-2">
                        <span
                          className={`metric-badge ${
                            isPositive
                              ? 'metric-badge--positive'
                              : isNegative
                                ? 'metric-badge--negative'
                                : 'metric-badge--neutral'
                          }`}
                        >
                          {formatDelta(delta)}
                        </span>
                      </td>
                    </React.Fragment>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
