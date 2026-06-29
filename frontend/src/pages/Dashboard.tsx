import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useBanks, useSimulations } from '../api/queries';
import BankCard from '../components/dashboard/BankCard';
import SimulationControls from '../components/dashboard/SimulationControls';
import { formatDuration } from '../utils/formatters';

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: banks, isLoading: banksLoading } = useBanks();
  const { data: simulations, isLoading: simsLoading } = useSimulations();
  const [_lastSimId, setLastSimId] = useState<string | null>(null);

  const handleSimulationCreated = (id: string) => {
    setLastSimId(id);
    // Navigate to the simulation view after a brief delay
    setTimeout(() => navigate(`/simulation/${id}`), 500);
  };

  return (
    <div className="space-y-6">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-2xl font-bold gradient-text mb-1">
          Collaborative Fraud Intelligence
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] max-w-2xl">
          Three independent banks collaboratively train a fraud detection model without sharing
          raw transaction data. Compare local-only models against the federated model to see
          why cross-institution collaboration improves detection.
        </p>
      </motion.div>

      {/* Bank Cards */}
      <div>
        <h2 className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
          Participating Institutions
        </h2>
        {banksLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="glass-card p-5 h-48 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {banks?.map((bank, idx) => (
              <BankCard key={bank.id} bank={bank} index={idx} />
            ))}
          </div>
        )}
      </div>

      {/* Controls + Recent Simulations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Simulation Controls */}
        <div className="lg:col-span-2">
          <SimulationControls onSimulationCreated={handleSimulationCreated} />
        </div>

        {/* Recent Simulations */}
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">
            Recent Simulations
          </h3>
          {simsLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-14 bg-[var(--color-bg-elevated)] rounded-lg animate-pulse" />
              ))}
            </div>
          ) : simulations && simulations.length > 0 ? (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {simulations.map((sim) => (
                <button
                  key={sim.id}
                  onClick={() => navigate(`/simulation/${sim.id}`)}
                  className="w-full text-left p-3 rounded-lg bg-[var(--color-bg-elevated)] hover:bg-[var(--color-bg-card-hover)] border border-[var(--color-border-subtle)] hover:border-[var(--color-accent-indigo)]/30 transition-all duration-200"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-[var(--color-text-secondary)]">
                      {sim.id.slice(0, 8)}...
                    </span>
                    <StatusBadge status={sim.status} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-[var(--color-text-muted)]">
                      {sim.current_round}/{sim.total_rounds} rounds
                    </span>
                    {sim.duration_seconds && (
                      <span className="text-[10px] text-[var(--color-text-muted)]">
                        {formatDuration(sim.duration_seconds)}
                      </span>
                    )}
                  </div>
                  {/* Progress bar */}
                  <div className="w-full h-1 bg-[var(--color-bg-primary)] rounded-full mt-2 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${sim.progress_pct}%`,
                        background: sim.status === 'completed'
                          ? 'var(--color-status-success)'
                          : sim.status === 'failed'
                            ? 'var(--color-status-error)'
                            : 'var(--color-accent-indigo)',
                      }}
                    />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-sm text-[var(--color-text-muted)]">No simulations yet</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                Configure and start your first federated training run
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-[var(--color-status-success)]/15 text-[var(--color-status-success)]',
    failed: 'bg-[var(--color-status-error)]/15 text-[var(--color-status-error)]',
    pending: 'bg-[var(--color-status-pending)]/15 text-[var(--color-status-pending)]',
    training_federated: 'bg-[var(--color-status-info)]/15 text-[var(--color-status-info)]',
    training_local: 'bg-[var(--color-status-info)]/15 text-[var(--color-status-info)]',
    generating_data: 'bg-[var(--color-status-warning)]/15 text-[var(--color-status-warning)]',
    evaluating: 'bg-[var(--color-accent-teal)]/15 text-[var(--color-accent-teal)]',
  };

  return (
    <span className={`text-[9px] px-2 py-0.5 rounded-full font-medium ${styles[status] ?? styles.pending}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}
