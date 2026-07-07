import { useState } from 'react';
import { motion } from 'framer-motion';
import { useCreateSimulation } from '../../api/queries';
import { DEFAULT_SIMULATION_CONFIG } from '../../utils/constants';
import type { SimulationConfig } from '../../api/types';

interface SimulationControlsProps {
  onSimulationCreated: (id: string) => void;
}

export default function SimulationControls({ onSimulationCreated }: SimulationControlsProps) {
  const [config, setConfig] = useState<Partial<SimulationConfig>>(DEFAULT_SIMULATION_CONFIG);
  const [isExpanded, setIsExpanded] = useState(() => {
    return typeof window !== 'undefined' && window.innerWidth >= 1024;
  });
  const createMutation = useCreateSimulation();

  const handleStart = () => {
    createMutation.mutate(config, {
      onSuccess: (data) => {
        onSimulationCreated(data.id);
      },
    });
  };

  const updateConfig = <K extends keyof SimulationConfig>(key: K, value: SimulationConfig[K]) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass-card p-6 h-full flex flex-col"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          Simulation Configuration
        </h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          {isExpanded ? 'Collapse ▴' : 'Expand ▾'}
        </button>
      </div>

      {/* Core Settings - always visible */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label className="block text-xs text-[var(--color-text-muted)] mb-1">Rounds</label>
          <input
            type="number"
            value={config.num_rounds}
            onChange={(e) => updateConfig('num_rounds', parseInt(e.target.value) || 10)}
            min={1}
            max={100}
            className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text-primary)] font-mono focus:outline-none focus:border-[var(--color-accent-indigo)] transition-colors"
          />
        </div>
        <div>
          <label className="block text-xs text-[var(--color-text-muted)] mb-1">Local Epochs</label>
          <input
            type="number"
            value={config.local_epochs}
            onChange={(e) => updateConfig('local_epochs', parseInt(e.target.value) || 3)}
            min={1}
            max={20}
            className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text-primary)] font-mono focus:outline-none focus:border-[var(--color-accent-indigo)] transition-colors"
          />
        </div>
        <div>
          <label className="block text-xs text-[var(--color-text-muted)] mb-1">Learning Rate</label>
          <input
            type="number"
            value={config.learning_rate}
            onChange={(e) => updateConfig('learning_rate', parseFloat(e.target.value) || 0.001)}
            step={0.0001}
            min={0.0001}
            max={1}
            className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text-primary)] font-mono focus:outline-none focus:border-[var(--color-accent-indigo)] transition-colors"
          />
        </div>
      </div>

      {/* Advanced Settings */}
      {isExpanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          transition={{ duration: 0.3 }}
          className="space-y-4 border-t border-[var(--color-border-subtle)] pt-4"
        >
          {/* Failure Simulation */}
          <div>
            <h4 className="text-xs font-medium text-[var(--color-text-secondary)] mb-3 uppercase tracking-wider">
              Failure Simulation
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.enable_dropout_simulation}
                  onChange={(e) => updateConfig('enable_dropout_simulation', e.target.checked)}
                  className="rounded border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-accent-indigo)] focus:ring-[var(--color-accent-indigo)]"
                />
                <span className="text-xs text-[var(--color-text-secondary)]">Client Dropout</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.enable_latency_simulation}
                  onChange={(e) => updateConfig('enable_latency_simulation', e.target.checked)}
                  className="rounded border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-accent-indigo)] focus:ring-[var(--color-accent-indigo)]"
                />
                <span className="text-xs text-[var(--color-text-secondary)]">Network Latency</span>
              </label>
            </div>
            {config.enable_dropout_simulation && (
              <div className="mt-2">
                <label className="block text-xs text-[var(--color-text-muted)] mb-1">
                  Dropout Probability: {((config.dropout_probability ?? 0.2) * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min={0}
                  max={80}
                  value={(config.dropout_probability ?? 0.2) * 100}
                  onChange={(e) => updateConfig('dropout_probability', parseInt(e.target.value) / 100)}
                  className="w-full accent-[var(--color-accent-indigo)]"
                />
              </div>
            )}
          </div>

          {/* Privacy */}
          <div>
            <h4 className="text-xs font-medium text-[var(--color-text-secondary)] mb-3 uppercase tracking-wider">
              Privacy Mechanism
            </h4>
            <select
              value={config.privacy_mechanism}
              onChange={(e) => updateConfig('privacy_mechanism', e.target.value as SimulationConfig['privacy_mechanism'])}
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-indigo)] transition-colors"
            >
              <option value="none">None</option>
              <option value="differential_privacy">Differential Privacy</option>
              <option value="secure_aggregation">Secure Aggregation</option>
              <option value="both">Both</option>
            </select>
            {(config.privacy_mechanism === 'differential_privacy' || config.privacy_mechanism === 'both') && (
              <div className="mt-2">
                <label className="block text-xs text-[var(--color-text-muted)] mb-1">
                  ε (Epsilon): {config.dp_epsilon}
                </label>
                <input
                  type="range"
                  min={0.1}
                  max={10}
                  step={0.1}
                  value={config.dp_epsilon}
                  onChange={(e) => updateConfig('dp_epsilon', parseFloat(e.target.value))}
                  className="w-full accent-[var(--color-accent-indigo)]"
                />
                <p className="text-[10px] text-[var(--color-text-muted)] mt-1">
                  Lower ε = stronger privacy, more noise, lower utility
                </p>
              </div>
            )}
          </div>

          {/* Data Volume */}
          <div>
            <h4 className="text-xs font-medium text-[var(--color-text-secondary)] mb-3 uppercase tracking-wider">
              Data Volume
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {(['bank_a_transactions', 'bank_b_transactions', 'bank_c_transactions'] as const).map((key, i) => (
                <div key={key}>
                  <label className="block text-xs text-[var(--color-text-muted)] mb-1">
                    Bank {String.fromCharCode(65 + i)}
                  </label>
                  <input
                    type="number"
                    value={config[key]}
                    onChange={(e) => updateConfig(key, parseInt(e.target.value) || 10000)}
                    min={1000}
                    max={200000}
                    step={1000}
                    className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text-primary)] font-mono focus:outline-none focus:border-[var(--color-accent-indigo)] transition-colors"
                  />
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Start Button */}
      <button
        onClick={handleStart}
        disabled={createMutation.isPending}
        className="mt-auto w-full py-2.5 rounded-lg font-medium text-sm text-white transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
        style={{
          background: 'linear-gradient(135deg, var(--color-accent-indigo), var(--color-accent-teal))',
        }}
      >
        {createMutation.isPending ? (
          <span className="flex items-center justify-center gap-2">
            <span className="animate-spin">⟳</span> Starting...
          </span>
        ) : (
          'Start Federated Training'
        )}
      </button>

      {createMutation.isError && (
        <p className="mt-2 text-xs text-[var(--color-status-error)]">
          Failed to start simulation. Is the backend running?
        </p>
      )}
    </motion.div>
  );
}
