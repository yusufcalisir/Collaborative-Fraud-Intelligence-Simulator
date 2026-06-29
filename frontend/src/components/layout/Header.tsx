export default function Header() {
  return (
    <header className="h-14 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/80 backdrop-blur-md flex items-center px-6 sticky top-0 z-40">
      <div className="flex-1">
        <h2 className="text-sm font-medium text-[var(--color-text-secondary)]">
          Collaborative Fraud Intelligence Simulator
        </h2>
      </div>
      <div className="flex items-center gap-4">
        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          API Docs ↗
        </a>
        <div className="w-px h-4 bg-[var(--color-border)]" />
        <span className="text-xs font-mono text-[var(--color-text-muted)]">v0.1.0</span>
      </div>
    </header>
  );
}
