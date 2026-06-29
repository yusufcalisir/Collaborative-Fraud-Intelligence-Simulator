import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useCase, useAddCaseNote, useUpdateCaseStatus } from '../api/queries';
import { CASE_STATUS_LABELS, PRIORITY_LABELS } from '../api/types';
import { useQueryClient } from '@tanstack/react-query';

const STATUS_COLORS: Record<string, string> = {
  open: '#3b82f6',
  assigned: '#8b5cf6',
  investigating: '#f59e0b',
  pending_review: '#f97316',
  escalated: '#ef4444',
  closed_confirmed: '#22c55e',
  closed_false_positive: '#6b7280',
};

const EVENT_ICONS: Record<string, string> = {
  created: '📋',
  assigned: '👤',
  status_changed: '🔄',
  note_added: '📝',
  alert_linked: '🔗',
};

export default function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { data: caseData, isLoading } = useCase(caseId);
  const addNote = useAddCaseNote();
  const updateStatus = useUpdateCaseStatus();
  const queryClient = useQueryClient();
  const [noteContent, setNoteContent] = useState('');

  const handleAddNote = async () => {
    if (!noteContent.trim() || !caseId) return;
    await addNote.mutateAsync({ caseId, author: 'analyst', content: noteContent });
    setNoteContent('');
    queryClient.invalidateQueries({ queryKey: ['case', caseId] });
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!caseId) return;
    try {
      await updateStatus.mutateAsync({ caseId, status: newStatus });
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
    } catch {
      // Status transition error handled by API
    }
  };

  if (isLoading) {
    return (
      <div className="glass-card p-8 text-center text-[var(--color-text-muted)]">
        Loading case...
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="glass-card p-8 text-center text-[var(--color-text-muted)]">
        Case not found
      </div>
    );
  }

  const statusColor = STATUS_COLORS[caseData.status] || '#6b7280';

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-5"
      >
        <div className="flex items-start justify-between mb-3">
          <div>
            <h1 className="text-xl font-bold mb-1">{caseData.title}</h1>
            <div className="flex items-center gap-3 text-sm text-[var(--color-text-muted)]">
              <span>ID: {caseData.id.slice(0, 8)}</span>
              <span>•</span>
              <span>{PRIORITY_LABELS[caseData.priority] || caseData.priority}</span>
              {caseData.assigned_to && (
                <>
                  <span>•</span>
                  <span>Assigned to {caseData.assigned_to}</span>
                </>
              )}
            </div>
          </div>
          <span
            className="px-3 py-1 rounded-lg text-sm font-bold text-white"
            style={{ backgroundColor: statusColor }}
          >
            {CASE_STATUS_LABELS[caseData.status] || caseData.status}
          </span>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-4 gap-4 mt-4">
          {[
            { label: 'Linked Alerts', value: caseData.alert_ids.length },
            { label: 'Notes', value: caseData.notes.length },
            { label: 'Timeline Events', value: caseData.timeline.length },
            { label: 'Duration', value: caseData.duration_hours ? `${caseData.duration_hours.toFixed(1)}h` : '—' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-lg font-bold">{stat.value}</div>
              <div className="text-[10px] uppercase text-[var(--color-text-muted)]">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Status Actions */}
        {caseData.is_open && (
          <div className="flex gap-2 mt-4 pt-3 border-t border-[var(--color-border)]">
            <span className="text-xs text-[var(--color-text-muted)] self-center mr-2">Change status:</span>
            {Object.entries(CASE_STATUS_LABELS)
              .filter(([k]) => k !== caseData.status)
              .slice(0, 4)
              .map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => handleStatusChange(value)}
                  disabled={updateStatus.isPending}
                  className="px-2 py-1 text-xs rounded border border-[var(--color-border)] hover:bg-[var(--color-surface-alt)] transition-colors disabled:opacity-50"
                >
                  {label}
                </button>
              ))}
          </div>
        )}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-5"
        >
          <h2 className="text-sm font-bold uppercase text-[var(--color-text-muted)] mb-4">
            Investigation Timeline
          </h2>
          <div className="space-y-3">
            {caseData.timeline.length === 0 ? (
              <p className="text-sm text-[var(--color-text-muted)]">No events yet</p>
            ) : (
              caseData.timeline.map((event, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex gap-3 items-start"
                >
                  <div className="text-lg mt-0.5">
                    {EVENT_ICONS[event.event_type] || '📌'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{event.description}</p>
                    <div className="flex gap-2 text-[10px] text-[var(--color-text-muted)] mt-0.5">
                      <span>{new Date(event.timestamp).toLocaleString()}</span>
                      <span>•</span>
                      <span>{event.actor}</span>
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </motion.div>

        {/* Notes */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-5"
        >
          <h2 className="text-sm font-bold uppercase text-[var(--color-text-muted)] mb-4">
            Investigation Notes
          </h2>

          {/* Add Note */}
          <div className="mb-4">
            <textarea
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="Add an investigation note..."
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--color-surface-alt)] border border-[var(--color-border)] text-[var(--color-text)] resize-none"
            />
            <button
              onClick={handleAddNote}
              disabled={!noteContent.trim() || addNote.isPending}
              className="mt-2 px-4 py-1.5 text-xs font-semibold rounded-lg bg-[var(--color-primary)] text-white hover:opacity-90 disabled:opacity-50"
            >
              {addNote.isPending ? 'Adding...' : 'Add Note'}
            </button>
          </div>

          {/* Existing Notes */}
          <div className="space-y-3">
            {caseData.notes.length === 0 ? (
              <p className="text-sm text-[var(--color-text-muted)]">No notes yet</p>
            ) : (
              caseData.notes.map((note) => (
                <div
                  key={note.id}
                  className="p-3 rounded-lg bg-[var(--color-surface-alt)] border border-[var(--color-border)]"
                >
                  <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mb-1">
                    <span className="font-semibold">{note.author}</span>
                    <span>{new Date(note.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{note.content}</p>
                </div>
              ))
            )}
          </div>
        </motion.div>
      </div>

      {/* Linked Alerts */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card p-5"
      >
        <h2 className="text-sm font-bold uppercase text-[var(--color-text-muted)] mb-3">
          Linked Alerts ({caseData.alert_ids.length})
        </h2>
        {caseData.alert_ids.length === 0 ? (
          <p className="text-sm text-[var(--color-text-muted)]">No alerts linked to this case</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {caseData.alert_ids.map((id) => (
              <span
                key={id}
                className="px-2 py-1 text-xs font-mono rounded bg-[var(--color-surface-alt)] border border-[var(--color-border)]"
              >
                {id.slice(0, 8)}
              </span>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
