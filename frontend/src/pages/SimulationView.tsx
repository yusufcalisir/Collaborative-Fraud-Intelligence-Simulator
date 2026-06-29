import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useSimulation, useTrainingRounds } from '../api/queries';
import MetricsComparison from '../components/dashboard/MetricsComparison';
import TrainingTimeline from '../components/dashboard/TrainingTimeline';
import FederatedTrainingAnimation from '../components/dashboard/FederatedTrainingAnimation';
import LossChart from '../components/charts/LossChart';
import ROCCurve from '../components/charts/ROCCurve';
import ConfusionMatrix from '../components/charts/ConfusionMatrix';
import FeatureImportance from '../components/charts/FeatureImportance';
import MetricsRadar from '../components/charts/MetricsRadar';
import { formatDuration, formatPercent } from '../utils/formatters';

export default function SimulationView() {
  const { id } = useParams<{ id: string }>();
  const { data: simulation, isLoading, isError, error } = useSimulation(id);
  const { data: rounds } = useTrainingRounds(id);

  // 404 — simulation expired (e.g. after backend redeploy)
  if (isError) {
    const is404 = (error as any)?.response?.status === 404;
    return (
      <div className="flex items-center justify-center h-96">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center glass-card p-8 max-w-md"
        >
          <div className="text-4xl mb-4">{is404 ? '🔄' : '⚠️'}</div>
          <h2 className="text-lg font-bold text-[var(--color-text-primary)] mb-2">
            {is404 ? 'Simulation Expired' : 'Error Loading Simulation'}
          </h2>
          <p className="text-sm text-[var(--color-text-muted)] mb-4">
            {is404
              ? 'This simulation is no longer available. The server was restarted and in-memory data was cleared. Please start a new simulation.'
              : 'An unexpected error occurred while loading the simulation.'}
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all duration-300"
            style={{
              background: 'linear-gradient(135deg, var(--color-accent-indigo), var(--color-accent-teal))',
            }}
          >
            ← Start New Simulation
          </Link>
        </motion.div>
      </div>
    );
  }

  if (isLoading || !simulation) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[var(--color-accent-indigo)] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-[var(--color-text-muted)]">Loading simulation...</p>
        </div>
      </div>
    );
  }

  const isComplete = simulation.status === 'completed';
  const isFailed = simulation.status === 'failed';
  const banks = simulation.banks ?? [];

  return (
    <div className="h-full flex flex-col gap-4 overflow-hidden">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 shrink-0"
      >
        <div>
          <Link
            to="/"
            className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors mb-1 inline-block"
          >
            ← Back to Dashboard
          </Link>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
            Simulation Results
          </h1>
          <p className="text-xs font-mono text-[var(--color-text-muted)] mt-0.5 break-all">{simulation.id}</p>
        </div>
        <div className="text-left sm:text-right shrink-0">
          <SimStatusBadge status={simulation.status} />
          {simulation.duration_seconds && (
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              Duration: {formatDuration(simulation.duration_seconds)}
            </p>
          )}
        </div>
      </motion.div>

      {/* Error */}
      {isFailed && simulation.error_message && (
        <div className="glass-card p-3 border-[var(--color-status-error)]/50 shrink-0">
          <p className="text-xs text-[var(--color-status-error)]">
            <span className="font-medium">Error: </span>
            {simulation.error_message}
          </p>
        </div>
      )}

      {/* Main Simulation View Area */}
      <div className="flex-1 min-h-0 overflow-y-auto pr-1 space-y-4 pb-4">
        {/* Main Dashboard Row */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
          {/* Left Panel: Animation */}
          <div className="lg:col-span-5 flex flex-col">
            <FederatedTrainingAnimation
              status={simulation.status}
              currentRound={simulation.current_round}
              totalRounds={simulation.total_rounds}
            />
          </div>

          {/* Right Panel: Stats & Charts */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            {/* Stats */}
            {banks.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 shrink-0">
                {[
                  {
                    label: 'Banks',
                    value: banks.length.toString(),
                    sub: 'participating',
                  },
                  {
                    label: 'Rounds',
                    value: `${simulation.current_round}/${simulation.total_rounds}`,
                    sub: 'communication rounds',
                  },
                  {
                    label: 'Avg Fraud Rate',
                    value: formatPercent(banks.reduce((s, b) => s + b.fraud_ratio, 0) / banks.length),
                    sub: 'across banks',
                  },
                  {
                    label: 'Status',
                    value: simulation.status.replace(/_/g, ' '),
                    sub: isComplete ? 'finished' : 'in progress',
                  },
                ].map((stat, i) => (
                  <motion.div
                    key={stat.label}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="glass-card p-3 flex flex-col justify-between"
                  >
                    <p className="text-[9px] text-[var(--color-text-muted)] uppercase tracking-wider">{stat.label}</p>
                    <p className="text-sm font-bold font-mono text-[var(--color-text-primary)] mt-0.5 truncate">{stat.value}</p>
                    <p className="text-[9px] text-[var(--color-text-muted)] truncate">{stat.sub}</p>
                  </motion.div>
                ))}
              </div>
            )}

            {/* Timeline & Loss chart */}
            {rounds && rounds.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 flex-1 min-h-0">
                <div className="sm:col-span-2 flex flex-col">
                  <LossChart rounds={rounds} />
                </div>
                <div className="sm:col-span-1 flex flex-col">
                  <TrainingTimeline
                    rounds={rounds}
                    currentRound={simulation.current_round}
                    totalRounds={simulation.total_rounds}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Detailed Metrics Comparison Charts (visible when complete) */}
        {isComplete && banks.length > 0 && banks[0]?.local_metrics && (
          <div className="border-t border-[var(--color-border-subtle)] pt-4 space-y-6">
            <MetricsComparison banks={banks} />
            <MetricsRadar banks={banks} />

            {/* ROC Curves — side by side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ROCCurve banks={banks} modelType="local" />
              <ROCCurve banks={banks} modelType="federated" />
            </div>

            {/* Confusion Matrices */}
            <div>
              <h2 className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
                Confusion Matrices — Local vs Federated
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {banks.map((bank) => (
                  <div key={bank.id} className="space-y-4">
                    <ConfusionMatrix bank={bank} modelType="local" />
                    <ConfusionMatrix bank={bank} modelType="federated" />
                  </div>
                ))}
              </div>
            </div>

            {/* Feature Importance */}
            <div>
              <h2 className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
                Feature Importance — Federated Model
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {banks.map((bank) => (
                  <FeatureImportance key={bank.id} bank={bank} modelType="federated" />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SimStatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    completed: 'var(--color-status-success)',
    failed: 'var(--color-status-error)',
    pending: 'var(--color-status-pending)',
    training_federated: 'var(--color-status-info)',
    training_local: 'var(--color-status-info)',
    generating_data: 'var(--color-status-warning)',
    evaluating: 'var(--color-accent-teal)',
  };

  const color = colorMap[status] ?? colorMap.pending;

  return (
    <span
      className="text-xs px-3 py-1 rounded-full font-medium capitalize"
      style={{
        background: `color-mix(in srgb, ${color} 15%, transparent)`,
        color: color,
      }}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}
