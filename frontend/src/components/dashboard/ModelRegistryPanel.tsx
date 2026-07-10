import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  useModelVersions,
  useRollbackModel,
  useCanaryHistory,
} from '../../api/queries';

interface ModelRegistryPanelProps {
  simulationId: string;
}

export default function ModelRegistryPanel({ simulationId }: ModelRegistryPanelProps) {
  const { data: versions, isLoading: loadingVersions, refetch: refetchVersions } = useModelVersions(simulationId);
  const { data: canaryHistory, isLoading: loadingCanary } = useCanaryHistory(simulationId);
  const rollbackMutation = useRollbackModel();
  const [activeTab, setActiveTab] = useState<'registry' | 'canary'>('registry');
  const [rollbackSuccess, setRollbackSuccess] = useState<string | null>(null);

  const activeVersion = versions?.find((v) => v.is_active);

  const handleRollback = async (version: number) => {
    try {
      await rollbackMutation.mutateAsync({ simulationId, version });
      setRollbackSuccess(`Successfully rolled back active global model to Version ${version}!`);
      refetchVersions();
      setTimeout(() => setRollbackSuccess(null), 5000);
    } catch (err: any) {
      console.error('Rollback failed:', err);
    }
  };

  const isLoading = loadingVersions || loadingCanary;

  if (isLoading && !versions) {
    return (
      <div className="glass-card p-5 animate-pulse">
        <div className="h-4 w-40 bg-[var(--color-bg-elevated)] rounded mb-4" />
        <div className="h-32 bg-[var(--color-bg-elevated)] rounded" />
      </div>
    );
  }

  return (
    <div className="glass-card p-5 flex flex-col gap-4">
      {/* Header and Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--color-border-subtle)] pb-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Model Registry & Canary Evaluation
          </h3>
          <p className="text-[10px] text-[var(--color-text-muted)]">
            Track, gate, and rollback collaboratively trained models.
          </p>
        </div>

        <div className="flex bg-[var(--color-bg-elevated)] p-0.5 rounded-lg self-start sm:self-auto">
          <button
            onClick={() => setActiveTab('registry')}
            className={`px-3 py-1 rounded-md text-xs transition-all ${
              activeTab === 'registry'
                ? 'bg-[var(--color-bg-card)] text-[var(--color-text-primary)] shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
            }`}
          >
            Registry & Rollback
          </button>
          <button
            onClick={() => setActiveTab('canary')}
            className={`px-3 py-1 rounded-md text-xs transition-all ${
              activeTab === 'canary'
                ? 'bg-[var(--color-bg-card)] text-[var(--color-text-primary)] shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
            }`}
          >
            Canary Decision Logs
          </button>
        </div>
      </div>

      {/* Success Notification */}
      <AnimatePresence>
        {rollbackSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-3 bg-[var(--color-status-success)]/15 border border-[var(--color-status-success)]/40 rounded-lg text-xs text-[var(--color-status-success)] font-medium flex items-center gap-2"
          >
            <span>✓</span> {rollbackSuccess}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Registry / Rollback view */}
      {activeTab === 'registry' && (
        <div className="space-y-4">
          {/* Active Model Summary Card */}
          {activeVersion ? (
            <div className="p-4 bg-gradient-to-tr from-[var(--color-accent-indigo)]/10 to-[var(--color-accent-teal)]/10 rounded-xl border border-[var(--color-accent-teal)]/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[var(--color-text-primary)]">
                    Active Production Model (v{activeVersion.version})
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[8px] bg-[var(--color-status-success)]/15 text-[var(--color-status-success)] font-bold uppercase tracking-wider animate-pulse">
                    Live
                  </span>
                </div>
                <p className="text-[10px] text-[var(--color-text-muted)]">
                  Created: {new Date(activeVersion.created_at).toLocaleString()}
                </p>
                <p className="text-[9px] font-mono text-[var(--color-text-muted)]">
                  Artifact: {activeVersion.filename}
                </p>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-3 gap-3 md:gap-6 bg-[var(--color-bg-card)]/40 p-3 rounded-lg border border-[var(--color-border-subtle)] shrink-0">
                <div>
                  <div className="text-[8px] text-[var(--color-text-muted)] uppercase">AUC-ROC</div>
                  <div className="text-xs font-bold font-mono text-[var(--color-accent-teal)]">
                    {activeVersion.metrics.auc_roc.toFixed(4)}
                  </div>
                </div>
                <div>
                  <div className="text-[8px] text-[var(--color-text-muted)] uppercase">F1-Score</div>
                  <div className="text-xs font-bold font-mono text-[var(--color-accent-indigo-light)]">
                    {activeVersion.metrics.f1_score.toFixed(4)}
                  </div>
                </div>
                <div>
                  <div className="text-[8px] text-[var(--color-text-muted)] uppercase">Loss</div>
                  <div className="text-xs font-bold font-mono text-[var(--color-text-primary)]">
                    {activeVersion.metrics.loss.toFixed(4)}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-6 border border-dashed border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-muted)]">
              No active version has been promoted to the registry yet. Run simulation communication rounds to start versioning.
            </div>
          )}

          {/* Versions Table */}
          {versions && versions.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-[var(--color-border-subtle)]">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[var(--color-bg-elevated)] border-b border-[var(--color-border-subtle)] text-[10px] text-[var(--color-text-muted)] uppercase">
                    <th className="p-3 font-semibold">Version</th>
                    <th className="p-3 font-semibold">Saved At</th>
                    <th className="p-3 font-semibold font-mono text-center">AUC-ROC</th>
                    <th className="p-3 font-semibold font-mono text-center">F1-Score</th>
                    <th className="p-3 font-semibold font-mono text-center">Loss</th>
                    <th className="p-3 font-semibold text-center">Status</th>
                    <th className="p-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((ver) => (
                    <tr
                      key={ver.version}
                      className={`border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-card-hover)] transition-colors ${
                        ver.is_active ? 'bg-[var(--color-accent-teal)]/5' : ''
                      }`}
                    >
                      <td className="p-3 font-semibold">v{ver.version}</td>
                      <td className="p-3 text-[var(--color-text-muted)]">
                        {new Date(ver.created_at).toLocaleTimeString()}
                      </td>
                      <td className="p-3 font-mono text-center font-semibold text-[var(--color-text-secondary)]">
                        {ver.metrics.auc_roc.toFixed(4)}
                      </td>
                      <td className="p-3 font-mono text-center text-[var(--color-text-secondary)]">
                        {ver.metrics.f1_score.toFixed(4)}
                      </td>
                      <td className="p-3 font-mono text-center text-[var(--color-text-secondary)]">
                        {ver.metrics.loss.toFixed(4)}
                      </td>
                      <td className="p-3 text-center">
                        {ver.is_active ? (
                          <span className="px-2 py-0.5 rounded text-[8px] bg-[var(--color-status-success)]/15 text-[var(--color-status-success)] font-semibold uppercase">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[8px] bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] font-semibold uppercase">
                            Archived
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          disabled={ver.is_active || rollbackMutation.isPending}
                          onClick={() => handleRollback(ver.version)}
                          className={`px-2.5 py-1 rounded text-[10px] font-medium transition-all ${
                            ver.is_active
                              ? 'bg-transparent text-[var(--color-text-muted)] cursor-not-allowed'
                              : 'bg-[var(--color-bg-elevated)] hover:bg-[var(--color-border)] text-[var(--color-text-primary)] active:scale-95'
                          }`}
                        >
                          {rollbackMutation.isPending ? 'Rolling back...' : 'Rollback'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Canary logs view */}
      {activeTab === 'canary' && (
        <div className="space-y-3">
          <div className="p-3 bg-[var(--color-bg-elevated)]/50 rounded-lg border border-[var(--color-border-subtle)] text-[10px] text-[var(--color-text-secondary)] leading-relaxed">
            💡 <strong>Canary Gate Rule:</strong> During the simulation loop, aggregated model updates must achieve a test AUC-ROC score greater than or equal to the currently promoted model (with a 0.5% grace tolerance) to be automatically deployed. If the quality check fails, the new model version is stored but is kept in an inactive (rejected) state.
          </div>

          <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
            {canaryHistory && canaryHistory.length > 0 ? (
              canaryHistory.map((item, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-lg border border-[var(--color-border-subtle)] flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-[var(--color-text-primary)]">
                        Round {item.round} (Candidate v{item.version})
                      </span>
                      {item.is_promoted ? (
                        <span className="px-1.5 py-0.5 rounded text-[8px] bg-[var(--color-status-success)]/15 text-[var(--color-status-success)] font-semibold uppercase">
                          Promoted
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded text-[8px] bg-[var(--color-status-error)]/15 text-[var(--color-status-error)] font-semibold uppercase">
                          Rejected
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-[var(--color-text-muted)]">
                      {item.reason}
                    </p>
                  </div>

                  <div className="flex items-center gap-4 shrink-0 bg-[var(--color-bg-card)]/50 px-3 py-1.5 rounded border border-[var(--color-border-subtle)] font-mono text-[10px]">
                    <div>
                      <span className="text-[9px] text-[var(--color-text-muted)]">Candidate:</span>{' '}
                      <span className="font-bold text-[var(--color-text-primary)]">
                        {item.candidate_auc.toFixed(4)}
                      </span>
                    </div>
                    <div className="h-3 w-[1px] bg-[var(--color-border-subtle)]" />
                    <div>
                      <span className="text-[9px] text-[var(--color-text-muted)]">Previous:</span>{' '}
                      <span className="font-bold text-[var(--color-text-secondary)]">
                        {item.promoted_auc > 0 ? item.promoted_auc.toFixed(4) : 'None'}
                      </span>
                    </div>
                  </div>
                </motion.div>
              ))
            ) : (
              <div className="text-center py-6 text-xs text-[var(--color-text-muted)]">
                Awaiting first communication round results to trigger canary checks...
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
