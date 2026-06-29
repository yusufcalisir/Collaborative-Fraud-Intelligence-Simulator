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
      className="glass-card p-4 hover:border-[var(--color-accent-indigo)]/50 transition-all duration-300"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold text-xs shrink-0"
            style={{ background: `linear-gradient(135deg, ${color}, ${color}88)` }}
          >
            {tierBadge[bank.tier] ?? 'M'}
          </div>
          <div>
            <h3 className="text-xs font-semibold text-[var(--color-text-primary)] leading-tight">
              {bank.name}
            </h3>
            <p className="text-[10px] text-[var(--color-text-muted)] capitalize">{bank.tier} bank</p>
          </div>
        </div>
        <span className="status-dot status-dot--active shrink-0 mt-1" />
      </div>

      {/* Stats */}
      <div className="space-y-2 text-xs">
        <div className="flex justify-between items-center">
          <span className="text-[11px] text-[var(--color-text-muted)]">Transactions</span>
          <span className="font-mono text-[var(--color-text-primary)]">
            {formatNumber(bank.default_transactions)}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-[11px] text-[var(--color-text-muted)]">Fraud Rate</span>
          <span className="font-mono text-[var(--color-accent-rose)]">
            {formatPercent(bank.default_fraud_ratio)}
          </span>
        </div>
      </div>

      {/* Fraud Pattern */}
      <div className="mt-2.5 pt-2 border-t border-[var(--color-border-subtle)]">
        <p className="text-[10px] text-[var(--color-text-muted)] leading-relaxed line-clamp-1 hover:line-clamp-none transition-all duration-200">
          <span className="text-[var(--color-text-secondary)] font-medium">Pattern: </span>
          {bank.fraud_pattern}
        </p>
      </div>

      {/* Characteristics */}
      <div className="mt-2 flex flex-wrap gap-1">
        {bank.characteristics.slice(0, 2).map((c) => (
          <span
            key={c}
            className="text-[9px] px-1.5 py-0.2 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]"
          >
            {c}
          </span>
        ))}
      </div>
    </motion.div>
  );
}
