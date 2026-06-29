import { Link, useLocation } from 'react-router-dom';

const NAV_SECTIONS = [
  {
    label: 'FL Simulator',
    items: [
      { path: '/', label: 'Dashboard', icon: '◈' },
    ],
  },
  {
    label: 'AML Intelligence',
    items: [
      { path: '/investigation', label: 'Investigation', icon: '📊' },
      { path: '/alerts', label: 'Alerts', icon: '🚨' },
      { path: '/cases', label: 'Cases', icon: '📋' },
      { path: '/scenarios', label: 'Scenarios', icon: '▶️' },
      { path: '/graph', label: 'Entity Graph', icon: '🕸️' },
    ],
  },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="fixed top-0 left-0 h-screen w-64 bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] flex flex-col z-50">
      {/* Logo */}
      <div className="p-5 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[var(--color-accent-indigo)] to-[var(--color-accent-teal)] flex items-center justify-center text-white font-bold text-sm">
            FI
          </div>
          <div>
            <h1 className="text-sm font-semibold text-[var(--color-text-primary)] leading-tight">
              Fraud Intelligence
            </h1>
            <p className="text-xs text-[var(--color-text-muted)]">Federated Simulator</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-4 overflow-y-auto">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <p className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
              {section.label}
            </p>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <li key={item.path}>
                    <Link
                      to={item.path}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                        isActive
                          ? 'bg-[var(--color-accent-indigo)]/15 text-[var(--color-accent-indigo-light)] border border-[var(--color-accent-indigo)]/30'
                          : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-card)]'
                      }`}
                    >
                      <span className="text-base">{item.icon}</span>
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[var(--color-border)]">
        <div className="glass-card p-3">
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Privacy-preserving cross-institution fraud detection via Federated Learning
          </p>
          <div className="mt-2 flex items-center gap-1.5">
            <span className="status-dot status-dot--active" />
            <span className="text-xs text-[var(--color-text-secondary)]">System Online</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
