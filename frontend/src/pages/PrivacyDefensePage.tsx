import { useState } from 'react';
import {
  useAggregationMethods,
  useAuditDLG,
  useAuditMIA,
  useAuditModelInversion,
  usePrivacyBudgetLog,
} from '../api/queries';
import type {
  AggregationMethodInfo,
  BudgetLogEntry,
  DLGAuditResult,
  MIAAuditResult,
  ModelInversionAuditResult,
} from '../api/types';

// ── Helpers ───────────────────────────────────────────────────

type RiskTier = 'safe' | 'low_risk' | 'moderate_risk' | 'high_risk';

const RISK_COLORS: Record<RiskTier, string> = {
  safe: '#10b981',
  low_risk: '#34d399',
  moderate_risk: '#f59e0b',
  high_risk: '#ef4444',
};
const RISK_LABELS: Record<RiskTier, string> = {
  safe: '🟢 Safe',
  low_risk: '🟢 Low Risk',
  moderate_risk: '🟡 Moderate Risk',
  high_risk: '🔴 High Risk',
};

function RiskBadge({ tier }: { tier: RiskTier }) {
  return (
    <span
      style={{
        background: RISK_COLORS[tier] + '22',
        color: RISK_COLORS[tier],
        border: `1px solid ${RISK_COLORS[tier]}55`,
      }}
      className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold"
    >
      {RISK_LABELS[tier]}
    </span>
  );
}

function ScoreBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const color = pct < 30 ? '#10b981' : pct < 60 ? '#f59e0b' : '#ef4444';
  return (
    <div className="w-full bg-[#1e293b] rounded-full h-2 mt-1">
      <div
        className="h-2 rounded-full transition-all duration-700"
        style={{ width: `${pct}%`, background: color }}
      />
    </div>
  );
}

// ── Sub-sections ──────────────────────────────────────────────

function DefenseSuiteSection({ methods }: { methods: AggregationMethodInfo[] }) {
  return (
    <section>
      <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        🛡️ Byzantine Defense Suite
        <span className="text-xs font-normal text-slate-400 ml-1">— Aggregation Method Catalogue</span>
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {methods.map((m) => (
          <div
            key={m.id}
            className="rounded-xl border p-4 flex flex-col gap-2 transition-all duration-200 hover:scale-[1.02]"
            style={{
              background: m.colluding_defense
                ? 'linear-gradient(135deg,#1e1b4b 0%,#1e293b 100%)'
                : '#0f172a',
              borderColor: m.colluding_defense ? '#6366f1' : m.byzantine_robust ? '#0ea5e9' : '#1e293b',
              boxShadow: m.colluding_defense ? '0 0 20px #6366f133' : 'none',
            }}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-semibold text-white text-sm leading-snug">{m.label}</span>
              <div className="flex flex-col items-end gap-1 shrink-0">
                {m.byzantine_robust && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/30 whitespace-nowrap">
                    Byzantine-Robust
                  </span>
                )}
                {m.colluding_defense && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 whitespace-nowrap">
                    Multi-Attacker Defense ✨
                  </span>
                )}
              </div>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">{m.description}</p>
            <p className="text-[10px] text-slate-500 mt-auto pt-1 border-t border-white/5">{m.paper}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// Sample gradient data for demo purposes
const SAMPLE_TRAIN_LOSSES = [0.02, 0.015, 0.018, 0.012, 0.025, 0.011, 0.019, 0.014];
const SAMPLE_TEST_LOSSES = [0.55, 0.62, 0.48, 0.70, 0.51, 0.66, 0.59, 0.44];
const SAMPLE_GRAD_NORMS = [0.8, 1.2, 0.95, 10.5, 0.7, 1.1, 8.3, 0.85];
const SAMPLE_ORIG_GRADS = Array.from({ length: 30 }, (_, i) => Math.sin(i) * 0.3);
const SAMPLE_RECV_GRADS = Array.from({ length: 30 }, (_, i) => Math.sin(i) * 0.3 + Math.random() * 0.05);

function AttackAuditPanel() {
  const auditMIA = useAuditMIA();
  const auditInversion = useAuditModelInversion();
  const auditDLG = useAuditDLG();

  const miaResult = auditMIA.data as MIAAuditResult | undefined;
  const invResult = auditInversion.data as ModelInversionAuditResult | undefined;
  const dlgResult = auditDLG.data as DLGAuditResult | undefined;

  return (
    <section>
      <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        ⚔️ Attack Audit Panel
        <span className="text-xs font-normal text-slate-400 ml-1">— Privacy Attack Evaluators</span>
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* MIA */}
        <div className="rounded-xl border border-slate-700 bg-[#0f172a] p-5 flex flex-col gap-3">
          <div>
            <h3 className="font-semibold text-white text-sm">Membership Inference Attack</h3>
            <p className="text-xs text-slate-500 mt-1">
              Can an adversary determine whether a transaction record was part of training data?
            </p>
          </div>
          {miaResult && (
            <div className="flex flex-col gap-2">
              <div className="flex justify-between text-xs text-slate-400">
                <span>Attack Success Rate (ASR)</span>
                <span className="text-white font-bold">{(miaResult.membership_leakage_asr * 100).toFixed(1)}%</span>
              </div>
              <ScoreBar value={miaResult.membership_leakage_asr} />
              <RiskBadge tier={miaResult.risk_tier as RiskTier} />
            </div>
          )}
          <button
            id="btn-run-mia-audit"
            onClick={() => auditMIA.mutate({ train_losses: SAMPLE_TRAIN_LOSSES, test_losses: SAMPLE_TEST_LOSSES })}
            disabled={auditMIA.isPending}
            className="mt-auto w-full py-2 rounded-lg text-sm font-semibold transition-all duration-200 disabled:opacity-50"
            style={{ background: auditMIA.isPending ? '#1e293b' : 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: 'white' }}
          >
            {auditMIA.isPending ? '⏳ Running MIA…' : '▶ Run MIA Audit'}
          </button>
        </div>

        {/* Model Inversion */}
        <div className="rounded-xl border border-slate-700 bg-[#0f172a] p-5 flex flex-col gap-3">
          <div>
            <h3 className="font-semibold text-white text-sm">Model Inversion Attack</h3>
            <p className="text-xs text-slate-500 mt-1">
              Can shared gradient norms expose transaction feature distributions?
            </p>
          </div>
          {invResult && (
            <div className="flex flex-col gap-2">
              <div className="flex justify-between text-xs text-slate-400">
                <span>Reconstruction Risk Score</span>
                <span className="text-white font-bold">{(invResult.reconstruction_risk_score * 100).toFixed(1)}%</span>
              </div>
              <ScoreBar value={invResult.reconstruction_risk_score} />
              <RiskBadge tier={invResult.risk_tier as RiskTier} />
              <p className="text-[10px] text-slate-500">
                Mean gradient norm: {invResult.mean_gradient_norm.toFixed(4)} &nbsp;|&nbsp;
                σ: {invResult.std_gradient_norm.toFixed(4)}
              </p>
            </div>
          )}
          <button
            id="btn-run-model-inversion-audit"
            onClick={() => auditInversion.mutate({ gradient_norms: SAMPLE_GRAD_NORMS })}
            disabled={auditInversion.isPending}
            className="mt-auto w-full py-2 rounded-lg text-sm font-semibold transition-all duration-200 disabled:opacity-50"
            style={{ background: auditInversion.isPending ? '#1e293b' : 'linear-gradient(135deg,#0ea5e9,#6366f1)', color: 'white' }}
          >
            {auditInversion.isPending ? '⏳ Running…' : '▶ Run Model Inversion Audit'}
          </button>
        </div>

        {/* DLG */}
        <div className="rounded-xl border border-slate-700 bg-[#0f172a] p-5 flex flex-col gap-3">
          <div>
            <h3 className="font-semibold text-white text-sm">DLG Gradient Leakage</h3>
            <p className="text-xs text-slate-500 mt-1">
              Are shared gradient vectors correlated enough to reconstruct raw data? (Zhu et al. 2019)
            </p>
          </div>
          {dlgResult && (
            <div className="flex flex-col gap-2">
              <div className="flex justify-between text-xs text-slate-400">
                <span>Pearson Leakage Score</span>
                <span className="text-white font-bold">{(dlgResult.dlg_leakage_score * 100).toFixed(1)}%</span>
              </div>
              <ScoreBar value={dlgResult.dlg_leakage_score} />
              <RiskBadge tier={dlgResult.risk_tier as RiskTier} />
              <p className="text-[10px] text-slate-500">
                Parameters audited: {dlgResult.params_audited}
              </p>
            </div>
          )}
          <button
            id="btn-run-dlg-audit"
            onClick={() => auditDLG.mutate({ original_gradients: SAMPLE_ORIG_GRADS, received_gradients: SAMPLE_RECV_GRADS })}
            disabled={auditDLG.isPending}
            className="mt-auto w-full py-2 rounded-lg text-sm font-semibold transition-all duration-200 disabled:opacity-50"
            style={{ background: auditDLG.isPending ? '#1e293b' : 'linear-gradient(135deg,#10b981,#0ea5e9)', color: 'white' }}
          >
            {auditDLG.isPending ? '⏳ Running DLG…' : '▶ Run DLG Audit'}
          </button>
        </div>

      </div>
    </section>
  );
}

function BudgetLogSection() {
  const { data: entries = [], isLoading } = usePrivacyBudgetLog(8.0);
  const hasExhausted = entries.some((e) => e.budget_exhausted);

  return (
    <section>
      <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
        📊 Enterprise Privacy Budget Log
        <span className="text-xs font-normal text-slate-400 ml-1">— Multi-Simulation ε Consumption</span>
      </h2>

      {hasExhausted && (
        <div className="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-400 flex items-center gap-2">
          ⚠️ <strong>Budget Exhaustion Risk Detected!</strong>&nbsp; One or more simulations have exceeded ε = 8.0.
          This may indicate a budget exhaustion attack pattern.
        </div>
      )}

      {isLoading ? (
        <div className="text-slate-500 text-sm animate-pulse py-8 text-center">Loading budget log…</div>
      ) : entries.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-700 py-12 text-center text-slate-500 text-sm">
          No active simulations tracked yet. Start a simulation to see ε consumption here.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-800/60">
                <th className="text-left px-4 py-3 text-xs text-slate-400 font-medium">Simulation ID</th>
                <th className="text-right px-4 py-3 text-xs text-slate-400 font-medium">Total ε</th>
                <th className="text-right px-4 py-3 text-xs text-slate-400 font-medium">δ</th>
                <th className="text-right px-4 py-3 text-xs text-slate-400 font-medium">Rounds</th>
                <th className="text-right px-4 py-3 text-xs text-slate-400 font-medium">ε/Round</th>
                <th className="text-center px-4 py-3 text-xs text-slate-400 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry: BudgetLogEntry) => (
                <tr
                  key={entry.simulation_id}
                  className={`border-b border-slate-800 transition-colors hover:bg-slate-800/40 ${entry.budget_exhausted ? 'bg-red-500/5' : ''}`}
                >
                  <td className="px-4 py-3 font-mono text-xs text-slate-300 truncate max-w-[200px]" title={entry.simulation_id}>
                    {entry.simulation_id.slice(0, 20)}…
                  </td>
                  <td className="px-4 py-3 text-right font-bold" style={{ color: entry.total_epsilon > 6 ? '#ef4444' : entry.total_epsilon > 3 ? '#f59e0b' : '#10b981' }}>
                    {entry.total_epsilon.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-400 text-xs">{entry.delta?.toExponential?.(1) ?? '—'}</td>
                  <td className="px-4 py-3 text-right text-slate-300">{entry.rounds_spent}</td>
                  <td className="px-4 py-3 text-right text-slate-400">{entry.epsilon_per_round?.toFixed(4) ?? '—'}</td>
                  <td className="px-4 py-3 text-center">
                    {entry.budget_exhausted ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">EXHAUSTED</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">OK</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// ── Main Page ─────────────────────────────────────────────────

export default function PrivacyDefensePage() {
  const { data: methods = [], isLoading: methodsLoading } = useAggregationMethods();
  const [activeTab, setActiveTab] = useState<'defense' | 'audit' | 'budget'>('defense');

  const tabs = [
    { id: 'defense' as const, label: '🛡️ Defense Suite', desc: 'Aggregation methods' },
    { id: 'audit' as const, label: '⚔️ Attack Audits', desc: 'MIA · Inversion · DLG' },
    { id: 'budget' as const, label: '📊 Budget Log', desc: 'ε consumption log' },
  ];

  return (
    <div
      className="min-h-screen p-6 md:p-8"
      style={{ background: 'linear-gradient(135deg,#020617 0%,#0a0e1a 50%,#030712 100%)' }}
    >
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">🔐</span>
          <div>
            <h1 className="text-2xl font-bold text-white">Privacy Defense Suite</h1>
            <p className="text-sm text-slate-400 mt-0.5">
              Advanced Byzantine defenses, attack evaluators, and enterprise privacy budget monitoring
            </p>
          </div>
        </div>

        {/* Tab Bar */}
        <div className="flex gap-2 mt-6 border-b border-slate-700/60 pb-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              id={`tab-privacy-defense-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-all duration-200 -mb-px border-b-2 ${
                activeTab === tab.id
                  ? 'text-indigo-400 border-indigo-500 bg-indigo-500/10'
                  : 'text-slate-500 border-transparent hover:text-slate-300 hover:border-slate-600'
              }`}
            >
              {tab.label}
              <span className="hidden md:inline text-[10px] ml-1 opacity-60">· {tab.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto space-y-8">
        {activeTab === 'defense' && (
          methodsLoading ? (
            <div className="text-slate-500 animate-pulse text-sm py-12 text-center">Loading defence catalogue…</div>
          ) : (
            <DefenseSuiteSection methods={methods} />
          )
        )}

        {activeTab === 'audit' && <AttackAuditPanel />}

        {activeTab === 'budget' && <BudgetLogSection />}
      </div>
    </div>
  );
}
