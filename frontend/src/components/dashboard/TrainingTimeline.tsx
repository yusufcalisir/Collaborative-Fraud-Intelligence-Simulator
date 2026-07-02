import { motion } from 'framer-motion';
import type { TrainingRound } from '../../api/types';
import { BANK_NAMES } from '../../api/types';
import { formatMs } from '../../utils/formatters';

interface TrainingTimelineProps {
  rounds: TrainingRound[];
  currentRound: number;
  totalRounds: number;
}

export default function TrainingTimeline({ rounds, currentRound, totalRounds }: TrainingTimelineProps) {
  return (
    <div className="glass-card p-5 h-[375px] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          Training Timeline
        </h3>
        <span className="text-xs font-mono text-[var(--color-text-muted)]">
          {currentRound}/{totalRounds} rounds
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-[var(--color-bg-elevated)] rounded-full mb-5 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{
            background: 'linear-gradient(90deg, var(--color-accent-indigo), var(--color-accent-teal))',
          }}
          initial={{ width: 0 }}
          animate={{ width: `${totalRounds > 0 ? (currentRound / totalRounds) * 100 : 0}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>

      {/* Round timeline */}
      <div className="space-y-2 flex-1 min-h-0 overflow-y-auto pr-1 flex flex-col">
        {rounds.length === 0 && (
          <div className="flex-1 flex flex-col justify-center items-center py-4 text-center">
            {/* Pulsing radar locator */}
            <div className="relative w-12 h-12 mb-3 flex items-center justify-center">
              <span className="absolute inline-flex h-full w-full rounded-full bg-[var(--color-accent-indigo)] opacity-20 animate-ping"></span>
              <div className="relative rounded-full w-7 h-7 bg-gradient-to-tr from-[var(--color-accent-indigo)] to-[var(--color-accent-teal)] flex items-center justify-center shadow-lg">
                <span className="text-xs">📡</span>
              </div>
            </div>
            
            <p className="text-xs font-semibold text-[var(--color-text-primary)] mb-0.5">
              Establishing Connections
            </p>
            <p className="text-[10px] text-[var(--color-text-muted)] max-w-[180px] mb-4">
              Awaiting initialization updates from client nodes...
            </p>
            
            {/* Status list */}
            <div className="w-full space-y-2 text-left bg-[var(--color-bg-card)]/50 p-3 rounded-lg border border-[var(--color-border-subtle)]">
              {[
                { id: 'bank_a', name: 'Meridian National' },
                { id: 'bank_b', name: 'Nexus Digital' },
                { id: 'bank_c', name: 'Heritage Regional' },
              ].map((bank) => (
                <div key={bank.id} className="flex items-center justify-between text-[10px]">
                  <span className="font-medium text-[var(--color-text-secondary)]">{bank.name}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-status-success)] opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[var(--color-status-success)]"></span>
                    </span>
                    <span className="text-[9px] text-[var(--color-text-muted)]">Connected</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {rounds.map((round, idx) => {
          const hasDropout = round.dropped_banks.length > 0;
          return (
            <motion.div
              key={round.round_number}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.05 }}
              className="flex items-start gap-3 p-2.5 rounded-lg hover:bg-[var(--color-bg-card-hover)] transition-colors"
            >
              {/* Round number */}
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
                  hasDropout
                    ? 'bg-[var(--color-accent-rose)]/20 text-[var(--color-accent-rose)]'
                    : 'bg-[var(--color-accent-indigo)]/20 text-[var(--color-accent-indigo-light)]'
                }`}
              >
                {round.round_number}
              </div>

              {/* Details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-[var(--color-text-primary)]">
                    Round {round.round_number}
                  </span>
                  <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                    {formatMs(round.duration_ms)}
                  </span>
                  {hasDropout && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--color-accent-rose)]/15 text-[var(--color-accent-rose)]">
                      dropout
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 mt-1">
                  <span className="text-[10px] text-[var(--color-text-muted)]">
                    Loss: <span className="font-mono text-[var(--color-text-secondary)]">{round.global_loss.toFixed(4)}</span>
                  </span>
                  <span className="text-[10px] text-[var(--color-text-muted)]">
                    Clients: {round.participating_banks.length}/3
                  </span>
                </div>

                {/* Participant badges */}
                <div className="flex gap-1 mt-1.5">
                  {round.participating_banks.map((bankId) => (
                    <span
                      key={bankId}
                      className="text-[8px] px-1.5 py-0.5 rounded bg-[var(--color-status-success)]/15 text-[var(--color-status-success)]"
                    >
                      {BANK_NAMES[bankId]?.split(' ')[0] ?? bankId}
                    </span>
                  ))}
                  {round.dropped_banks.map((bankId) => (
                    <span
                      key={bankId}
                      className="text-[8px] px-1.5 py-0.5 rounded bg-[var(--color-status-error)]/15 text-[var(--color-status-error)] line-through"
                    >
                      {BANK_NAMES[bankId]?.split(' ')[0] ?? bankId}
                    </span>
                  ))}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
