import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useCases, useCreateCase } from '../api/queries';
import { CASE_STATUS_LABELS, PRIORITY_LABELS } from '../api/types';

const PRIORITY_COLORS: Record<string, string> = {
  p1_critical: '#ef4444',
  p2_high: '#f97316',
  p3_medium: '#f59e0b',
  p4_low: '#3b82f6',
};

export default function CasesPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { data: cases, isLoading, refetch } = useCases({
    status: statusFilter || undefined,
  });
  const createCase = useCreateCase();

  const handleCreate = async (title: string, priority: string) => {
    const result = await createCase.mutateAsync({ title, priority });
    setShowCreateModal(false);
    refetch();
    navigate(`/cases/${result.id}`);
  };

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-2xl font-bold gradient-text mb-1">
          Case Management
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] max-w-2xl">
          Investigation cases linking alerts to investigation workflows. Track cases
          from initial detection through resolution.
        </p>
      </motion.div>

      {/* Controls */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex gap-3 flex-wrap items-center"
      >
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="glass-card px-3 py-2 text-sm rounded-lg bg-[var(--color-bg-card)] border border-[var(--color-border)] text-[var(--color-text)]"
        >
          <option value="">All Statuses</option>
          {Object.entries(CASE_STATUS_LABELS).map(([val, label]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>

        <button
          onClick={() => setShowCreateModal(true)}
          className="ml-auto px-4 py-2 text-sm font-semibold rounded-lg bg-[var(--color-primary)] text-white hover:opacity-90 transition-opacity"
        >
          + New Case
        </button>

        <span className="text-sm text-[var(--color-text-muted)]">
          {cases?.length ?? 0} cases
        </span>
      </motion.div>

      {/* Case Grid */}
      {isLoading ? (
        <div className="glass-card p-8 text-center text-[var(--color-text-muted)]">Loading cases...</div>
      ) : !cases?.length ? (
        <div className="glass-card p-8 text-center text-[var(--color-text-muted)]">
          <p className="text-lg mb-2">No cases yet</p>
          <p className="text-sm">Create a case to start tracking investigations.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {cases.map((c, i) => {
            const prioColor = PRIORITY_COLORS[c.priority] || '#6b7280';
            return (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                onClick={() => navigate(`/cases/${c.id}`)}
                className="glass-card p-4 cursor-pointer hover:scale-[1.02] transition-transform"
              >
                <div className="flex items-start justify-between mb-3">
                  <span
                    className="px-2 py-0.5 rounded text-xs font-bold text-white"
                    style={{ backgroundColor: prioColor }}
                  >
                    {PRIORITY_LABELS[c.priority] || c.priority}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      c.is_open
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-gray-500/20 text-gray-400'
                    }`}
                  >
                    {CASE_STATUS_LABELS[c.status] || c.status}
                  </span>
                </div>
                <h3 className="font-semibold mb-2 line-clamp-2">{c.title}</h3>
                <div className="flex justify-between text-xs text-[var(--color-text-muted)]">
                  <span>{c.alert_count} alerts linked</span>
                  <span>{new Date(c.created_at).toLocaleDateString()}</span>
                </div>
                {c.assigned_to && (
                  <div className="mt-2 text-xs text-[var(--color-text-muted)]">
                    Assigned to: <span className="text-[var(--color-text)]">{c.assigned_to}</span>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateCaseModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreate}
          isLoading={createCase.isPending}
        />
      )}
    </div>
  );
}

function CreateCaseModal({
  onClose,
  onCreate,
  isLoading,
}: {
  onClose: () => void;
  onCreate: (title: string, priority: string) => void;
  isLoading: boolean;
}) {
  const [title, setTitle] = useState('');
  const [priority, setPriority] = useState('p3_medium');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-card p-6 w-full max-w-md space-y-4"
      >
        <h2 className="text-lg font-bold">New Investigation Case</h2>

        <div>
          <label className="block text-xs text-[var(--color-text-muted)] mb-1">Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Suspicious transaction cluster at Meridian..."
            className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--color-surface-alt)] border border-[var(--color-border)] text-[var(--color-text)]"
          />
        </div>

        <div>
          <label className="block text-xs text-[var(--color-text-muted)] mb-1">Priority</label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--color-surface-alt)] border border-[var(--color-border)] text-[var(--color-text)]"
          >
            {Object.entries(PRIORITY_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </div>

        <div className="flex gap-3 justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-surface-alt)]"
          >
            Cancel
          </button>
          <button
            onClick={() => title && onCreate(title, priority)}
            disabled={!title || isLoading}
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-[var(--color-primary)] text-white hover:opacity-90 disabled:opacity-50"
          >
            {isLoading ? 'Creating...' : 'Create Case'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
