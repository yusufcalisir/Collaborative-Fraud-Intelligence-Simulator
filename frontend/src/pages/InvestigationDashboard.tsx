import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  useDashboardStats,
  useAlertsBySeverity,
  useAlertsByBank,
  useIntelligenceStats,
  useAuditLogs,
} from '../api/queries';
import { BANK_NAMES, SEVERITY_COLORS } from '../api/types';

export default function InvestigationDashboard() {
  const { data: stats, isLoading } = useDashboardStats();
  const { data: alertsBySeverity } = useAlertsBySeverity();
  const { data: alertsByBank } = useAlertsByBank();
  const { data: intelStats } = useIntelligenceStats();
  const { data: auditLogs } = useAuditLogs();

  const statCards = stats ? [
    { label: 'Total Alerts', value: stats.total_alerts, icon: '🚨', color: '#f59e0b', href: '/alerts' },
    { label: 'Critical Alerts', value: stats.critical_alerts, icon: '🔴', color: '#ef4444', href: '/alerts' },
    { label: 'Open Cases', value: stats.open_cases, icon: '📋', color: '#6366f1', href: '/cases' },
    { label: 'Entities', value: stats.total_entities, icon: '👤', color: '#14b8a6', href: '/graph' },
    { label: 'Intelligence Items', value: stats.shared_intelligence_items, icon: '🔗', color: '#8b5cf6', href: '/alerts' },
    { label: 'Graph Clusters', value: stats.graph_clusters, icon: '🕸️', color: '#ec4899', href: '/graph' },
    { label: 'Active Scenarios', value: stats.active_scenarios, icon: '▶️', color: '#06b6d4', href: '/scenarios' },
    { label: 'Cross-Institution', value: stats.cross_institution_matches, icon: '🏦', color: '#f97316', href: '/graph' },
  ] : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-2xl font-bold gradient-text mb-1">
          Investigation Dashboard
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] max-w-2xl">
          Aggregated view of the collaborative AML intelligence platform.
          Real-time statistics across alerts, cases, entities, and intelligence.
        </p>
      </motion.div>

      {/* Stat Cards */}
      {isLoading ? (
        <div className="glass-card p-8 text-center text-[var(--color-text-muted)]">Loading dashboard...</div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {statCards.map((card, i) => (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Link
                to={card.href}
                className="glass-card p-4 block hover:scale-[1.03] transition-transform"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">{card.icon}</span>
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: card.color }}
                  />
                </div>
                <div className="text-2xl font-bold" style={{ color: card.color }}>
                  {card.value}
                </div>
                <div className="text-[10px] uppercase text-[var(--color-text-muted)] mt-1">
                  {card.label}
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Alerts by Severity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-5"
        >
          <h3 className="text-sm font-bold uppercase text-[var(--color-text-muted)] mb-4">
            Alerts by Severity
          </h3>
          {alertsBySeverity && Object.keys(alertsBySeverity).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(alertsBySeverity)
                .sort(([a], [b]) => {
                  const order = ['critical', 'high', 'medium', 'low', 'info'];
                  return order.indexOf(a) - order.indexOf(b);
                })
                .map(([severity, count]) => {
                  const total = Object.values(alertsBySeverity).reduce((a, b) => a + b, 0);
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  const color = SEVERITY_COLORS[severity] || '#6b7280';
                  return (
                    <div key={severity}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="capitalize font-medium">{severity}</span>
                        <span className="font-mono">{count}</span>
                      </div>
                      <div className="h-2 bg-[var(--color-surface-alt)] rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.8 }}
                          className="h-full rounded-full"
                          style={{ backgroundColor: color }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-text-muted)]">No alert data yet</p>
          )}
        </motion.div>

        {/* Alerts by Bank */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass-card p-5"
        >
          <h3 className="text-sm font-bold uppercase text-[var(--color-text-muted)] mb-4">
            Alerts by Bank
          </h3>
          {alertsByBank && Object.keys(alertsByBank).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(alertsByBank).map(([bankId, count]) => {
                const total = Object.values(alertsByBank).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? (count / total) * 100 : 0;
                return (
                  <div key={bankId}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium">{BANK_NAMES[bankId] || bankId}</span>
                      <span className="font-mono">{count}</span>
                    </div>
                    <div className="h-2 bg-[var(--color-surface-alt)] rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8 }}
                        className="h-full rounded-full bg-[var(--color-primary)]"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-text-muted)]">No bank data yet</p>
          )}
        </motion.div>

        {/* Intelligence Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card p-5"
        >
          <h3 className="text-sm font-bold uppercase text-[var(--color-text-muted)] mb-4">
            Shared Intelligence
          </h3>
          {intelStats && intelStats.total_items > 0 ? (
            <div className="space-y-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-[var(--color-primary)]">
                  {intelStats.total_items}
                </div>
                <div className="text-xs text-[var(--color-text-muted)]">Total Intelligence Items</div>
              </div>

              <div className="text-center">
                <div className="text-lg font-bold">
                  {(intelStats.avg_risk_indicator * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-[var(--color-text-muted)]">Avg Risk Indicator</div>
              </div>

              <div>
                <h4 className="text-[10px] uppercase text-[var(--color-text-muted)] mb-1">By Type</h4>
                {Object.entries(intelStats.items_by_type).map(([type, count]) => (
                  <div key={type} className="flex justify-between text-xs py-0.5">
                    <span className="text-[var(--color-text-muted)] capitalize">
                      {type.replace(/_/g, ' ')}
                    </span>
                    <span className="font-mono">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <div className="text-3xl mb-2">🔗</div>
              <p className="text-sm text-[var(--color-text-muted)]">
                No shared intelligence yet. Run a scenario to generate data.
              </p>
            </div>
          )}
        </motion.div>
      </div>

      {/* Quick Links */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="glass-card p-5"
      >
        <h3 className="text-sm font-bold uppercase text-[var(--color-text-muted)] mb-3">
          Quick Actions
        </h3>
        <div className="flex flex-wrap gap-3">
          {[
            { label: '▶ Run Fraud Ring Scenario', href: '/scenarios', color: '#6366f1' },
            { label: '🔍 View Alerts', href: '/alerts', color: '#f59e0b' },
            { label: '📋 Open Cases', href: '/cases', color: '#14b8a6' },
            { label: '🕸️ Explore Graph', href: '/graph', color: '#ec4899' },
            { label: '🏠 FL Simulator', href: '/', color: '#3b82f6' },
          ].map((link) => (
            <Link
              key={link.label}
              to={link.href}
              className="px-4 py-2 text-sm rounded-lg border border-[var(--color-border)] hover:border-transparent transition-all"
              style={{ '--hover-bg': link.color } as React.CSSProperties}
              onMouseEnter={(e) => {
                (e.target as HTMLElement).style.backgroundColor = link.color + '20';
                (e.target as HTMLElement).style.borderColor = link.color;
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLElement).style.backgroundColor = '';
                (e.target as HTMLElement).style.borderColor = '';
              }}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </motion.div>

      {/* Audit Logs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="glass-card p-5 mt-6"
      >
        <h3 className="text-sm font-bold uppercase text-[var(--color-text-muted)] mb-4 flex items-center gap-2">
          🕵️ Investigator Activity Audit Trail (Compliance Log)
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-[var(--color-text-muted)]">
                <th className="py-2">Investigator</th>
                <th className="py-2">Action</th>
                <th className="py-2">Target ID</th>
                <th className="py-2">Timestamp</th>
                <th className="py-2 text-right">Details</th>
              </tr>
            </thead>
            <tbody>
              {!auditLogs || auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-[var(--color-text-muted)]">
                    No activity logs recorded yet.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log: any) => (
                  <tr key={log.id} className="border-b border-[var(--color-border)]/50 hover:bg-[var(--color-surface-alt)]/20 transition-colors">
                    <td className="py-2 font-semibold text-[var(--color-primary)]">{log.investigator}</td>
                    <td className="py-2 uppercase font-mono text-[10px]">{log.action.replace(/_/g, ' ')}</td>
                    <td className="py-2 font-mono text-gray-500">{log.target_id.slice(0, 8)}...</td>
                    <td className="py-2 text-[var(--color-text-muted)]">{new Date(log.timestamp).toLocaleString()}</td>
                    <td className="py-2 text-right text-[10px] text-gray-400 max-w-xs truncate">
                      {JSON.stringify(log.metadata)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
