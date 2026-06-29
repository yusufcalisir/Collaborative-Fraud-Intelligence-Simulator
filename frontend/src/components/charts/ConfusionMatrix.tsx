import type { BankResult } from '../../api/types';
import { BANK_COLORS } from '../../api/types';

interface ConfusionMatrixProps {
  bank: BankResult;
  modelType: 'local' | 'federated';
}

export default function ConfusionMatrix({ bank, modelType }: ConfusionMatrixProps) {
  const metrics = modelType === 'local' ? bank.local_metrics : bank.federated_metrics;
  if (!metrics) return null;

  const cm = metrics.confusion_matrix;
  const tn = cm[0]?.[0] ?? 0;
  const fp = cm[0]?.[1] ?? 0;
  const fn = cm[1]?.[0] ?? 0;
  const tp = cm[1]?.[1] ?? 0;
  const total = tn + fp + fn + tp || 1;

  const cells = [
    { label: 'TN', value: tn, row: 0, col: 0, intensity: tn / total },
    { label: 'FP', value: fp, row: 0, col: 1, intensity: fp / total, isError: true },
    { label: 'FN', value: fn, row: 1, col: 0, intensity: fn / total, isError: true },
    { label: 'TP', value: tp, row: 1, col: 1, intensity: tp / total },
  ];

  const color = BANK_COLORS[bank.id] ?? '#6366f1';

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-1">
        Confusion Matrix
      </h3>
      <p className="text-[10px] text-[var(--color-text-muted)] mb-3">
        {bank.name} — {modelType === 'local' ? 'Local' : 'Federated'}
      </p>

      <div className="flex justify-center">
        <div>
          {/* Column labels */}
          <div className="flex ml-16">
            <div className="w-20 text-center text-[10px] text-[var(--color-text-muted)]">Pred: Legit</div>
            <div className="w-20 text-center text-[10px] text-[var(--color-text-muted)]">Pred: Fraud</div>
          </div>

          {/* Rows */}
          {[0, 1].map((row) => (
            <div key={row} className="flex items-center">
              <div className="w-16 text-right pr-2 text-[10px] text-[var(--color-text-muted)]">
                {row === 0 ? 'Actual: Legit' : 'Actual: Fraud'}
              </div>
              {[0, 1].map((col) => {
                const cell = cells.find((c) => c.row === row && c.col === col)!;
                const bgOpacity = Math.min(0.6, cell.intensity * 3);
                const bgColor = cell.isError
                  ? `rgba(244, 63, 94, ${bgOpacity})`
                  : `rgba(${parseInt(color.slice(1, 3), 16)}, ${parseInt(color.slice(3, 5), 16)}, ${parseInt(color.slice(5, 7), 16)}, ${bgOpacity})`;

                return (
                  <div
                    key={col}
                    className="w-20 h-16 flex flex-col items-center justify-center rounded-md m-0.5 border border-[var(--color-border-subtle)]"
                    style={{ background: bgColor }}
                  >
                    <span className="text-lg font-bold font-mono text-[var(--color-text-primary)]">
                      {cell.value.toLocaleString()}
                    </span>
                    <span className="text-[9px] text-[var(--color-text-muted)]">{cell.label}</span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
