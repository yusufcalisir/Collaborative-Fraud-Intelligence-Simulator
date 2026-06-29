import { motion } from 'framer-motion';
import type { BankInfo } from '../../api/types';
import { BANK_COLORS } from '../../api/types';
import { formatPercent, formatNumber } from '../../utils/formatters';

interface BankCardProps {
  bank: BankInfo;
  index: number;
}

export default function BankCard({ bank, index }: BankCardProps) {
  const color = BANK_COLORS[bank.id] ?? '#6366f1';
  const tierBadge: Record<string, string> = {
    large: 'L',
    medium: 'M',
    small: 'S',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="glass-card p-5 hover:border-[var(--color-accent-indigo)]/50 transition-all duration-300"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold text-sm"
            style={{ background: `linear-gradient(135deg, ${color}, ${color}88)` }}
          >
            {tierBadge[bank.tier] ?? 'M'}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
              {bank.name}
            </h3>
            <p className="text-xs text-[var(--color-text-muted)] capitalize">{bank.tier} bank</p>
          </div>
        </div>
        <span className="status-dot status-dot--active" />
      </div>

      {/* Stats */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-xs text-[var(--color-text-muted)]">Transactions</span>
          <span className="text-sm font-mono text-[var(--color-text-primary)]">
            {formatNumber(bank.default_transactions)}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-[var(--color-text-muted)]">Fraud Rate</span>
          <span className="text-sm font-mono text-[var(--color-accent-rose)]">
            {formatPercent(bank.default_fraud_ratio)}
          </span>
        </div>
      </div>

      {/* Fraud Pattern */}
      <div className="mt-4 pt-3 border-t border-[var(--color-border-subtle)]">
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
          <span className="text-[var(--color-text-secondary)] font-medium">Pattern: </span>
          {bank.fraud_pattern}
        </p>
      </div>

      {/* Characteristics */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {bank.characteristics.slice(0, 2).map((c) => (
          <span
            key={c}
            className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]"
          >
            {c}
          </span>
        ))}
      </div>
    </motion.div>
  );
}
