import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { useBankDistributions } from '../../api/queries';
import { BANK_COLORS, BANK_NAMES } from '../../api/types';

const TABS = [
  { id: 'amount', label: 'Transaction Amount', icon: '💰' },
  { id: 'hourly', label: 'Hourly Fraud Pattern', icon: '🕐' },
  { id: 'merchant', label: 'Merchant Risk', icon: '🏪' },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function DataDriftPanel() {
  const { data, isLoading } = useBankDistributions();
  const [activeTab, setActiveTab] = useState<TabId>('amount');

  // Prepare chart data
  const amountData = useMemo(() => {
    if (!data) return [];
    const bankA = data.banks.bank_a?.amount_histogram;
    const bankB = data.banks.bank_b?.amount_histogram;
    const bankC = data.banks.bank_c?.amount_histogram;
    if (!bankA || !bankB || !bankC) return [];

    return bankA.bins.slice(0, -1).map((bin, i) => ({
      bin: bin < 1000 ? `$${Math.round(bin)}` : `$${(bin / 1000).toFixed(1)}k`,
      binValue: bin,
      bank_a: bankA.counts[i] ?? 0,
      bank_b: bankB.counts[i] ?? 0,
      bank_c: bankC.counts[i] ?? 0,
    }));
  }, [data]);

  const hourlyData = useMemo(() => {
    if (!data) return [];
    const bankA = data.banks.bank_a?.hourly_fraud_rate;
    const bankB = data.banks.bank_b?.hourly_fraud_rate;
    const bankC = data.banks.bank_c?.hourly_fraud_rate;
    if (!bankA || !bankB || !bankC) return [];

    return bankA.hours.map((h, i) => {
      const aTotal = bankA.total[i] ?? 0;
      const bTotal = bankB.total[i] ?? 0;
      const cTotal = bankC.total[i] ?? 0;
      const aFraud = bankA.fraud[i] ?? 0;
      const bFraud = bankB.fraud[i] ?? 0;
      const cFraud = bankC.fraud[i] ?? 0;
      return {
        hour: `${h.toString().padStart(2, '0')}:00`,
        bank_a: aTotal > 0 ? +((aFraud / aTotal) * 100).toFixed(2) : 0,
        bank_b: bTotal > 0 ? +((bFraud / bTotal) * 100).toFixed(2) : 0,
        bank_c: cTotal > 0 ? +((cFraud / cTotal) * 100).toFixed(2) : 0,
      };
    });
  }, [data]);

  const merchantData = useMemo(() => {
    if (!data) return [];
    // Collect all unique categories across banks
    const allCategories = new Set<string>();
    Object.values(data.banks).forEach((bank) => {
      bank.merchant_risk.categories.forEach((c) => allCategories.add(c));
    });

    // Build data for each category
    return Array.from(allCategories)
      .slice(0, 10)
      .map((cat) => {
        const row: Record<string, string | number> = {
          category: cat.replace(/_/g, ' '),
        };
        for (const [bankId, bankData] of Object.entries(data.banks)) {
          const idx = bankData.merchant_risk.categories.indexOf(cat);
          const rate = idx >= 0 ? (bankData.merchant_risk.fraud_rates[idx] ?? 0) : 0;
          row[bankId] = +(rate * 100).toFixed(2);
        }
        return row;
      })
      .sort((a, b) => {
        const sumA = (a.bank_a as number) + (a.bank_b as number) + (a.bank_c as number);
        const sumB = (b.bank_a as number) + (b.bank_b as number) + (b.bank_c as number);
        return sumB - sumA;
      });
  }, [data]);

  const nonIIDScore = data?.divergence_summary?.overall_non_iid_score ?? 0;
  const ksStats = data?.divergence_summary?.amount_ks_statistic ?? {};

  if (isLoading) {
    return (
      <div className="glass-card p-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-4 w-48 bg-[var(--color-bg-elevated)] rounded animate-pulse" />
          <div className="h-6 w-20 bg-[var(--color-bg-elevated)] rounded-full animate-pulse ml-auto" />
        </div>
        <div className="h-48 bg-[var(--color-bg-elevated)] rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-card p-4 overflow-hidden"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <h2 className="text-xs font-semibold text-[var(--color-text-primary)] uppercase tracking-wider">
            Non-IID Data Distribution
          </h2>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
            Visualizing data heterogeneity across banks — each institution sees different fraud patterns
          </p>
        </div>

        {/* Non-IID Score Badge */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.5, type: 'spring', stiffness: 200 }}
          className="relative group shrink-0"
        >
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border cursor-help"
            style={{
              background: `linear-gradient(135deg, rgba(99,102,241,0.1), rgba(20,184,166,0.1))`,
              borderColor: `rgba(99,102,241,0.3)`,
              color: 'var(--color-accent-indigo-light)',
            }}
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-accent-indigo)] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--color-accent-indigo)]" />
            </span>
            Non-IID Score: {(nonIIDScore * 100).toFixed(0)}%
          </div>
          {/* Tooltip */}
          <div className="absolute right-0 top-full mt-2 w-64 p-3 rounded-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border-subtle)] shadow-xl opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity duration-200 z-50">
            <p className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed mb-2">
              <span className="font-semibold text-[var(--color-text-primary)]">Kolmogorov-Smirnov Divergence</span>
              <br />
              Measures statistical distance between bank transaction distributions. Higher = more heterogeneous (Non-IID) data.
            </p>
            <div className="space-y-1">
              {Object.entries(ksStats).map(([pair, value]) => (
                <div key={pair} className="flex justify-between text-[9px]">
                  <span className="text-[var(--color-text-muted)] capitalize">
                    {pair.replace(/_/g, ' ').replace('vs', '↔')}
                  </span>
                  <span className="font-mono text-[var(--color-text-primary)]">{(value * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-[var(--color-bg-primary)] rounded-lg p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-medium transition-all duration-200 ${
              activeTab === tab.id
                ? 'bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] shadow-sm border border-[var(--color-border-subtle)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            <span>{tab.icon}</span>
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Chart Area */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -10 }}
          transition={{ duration: 0.2 }}
          className="h-56 sm:h-64"
        >
          {activeTab === 'amount' && <AmountChart data={amountData} />}
          {activeTab === 'hourly' && <HourlyChart data={hourlyData} />}
          {activeTab === 'merchant' && <MerchantChart data={merchantData} />}
        </motion.div>
      </AnimatePresence>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-3 pt-3 border-t border-[var(--color-border-subtle)]">
        {(['bank_a', 'bank_b', 'bank_c'] as const).map((bankId) => (
          <div key={bankId} className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-muted)]">
            <div
              className="w-2.5 h-2.5 rounded-sm"
              style={{ backgroundColor: BANK_COLORS[bankId] }}
            />
            {BANK_NAMES[bankId]}
          </div>
        ))}
      </div>
    </motion.div>
  );
}

// ── Sub-Charts ──────────────────────────────────────

function AmountChart({ data }: { data: Record<string, unknown>[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <defs>
          {(['bank_a', 'bank_b', 'bank_c'] as const).map((bankId) => (
            <linearGradient key={bankId} id={`grad-${bankId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={BANK_COLORS[bankId]} stopOpacity={0.3} />
              <stop offset="95%" stopColor={BANK_COLORS[bankId]} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" opacity={0.5} />
        <XAxis
          dataKey="bin"
          tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }}
          interval="preserveStartEnd"
          tickLine={false}
          axisLine={{ stroke: 'var(--color-border-subtle)' }}
        />
        <YAxis
          tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
          width={35}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: '8px',
            fontSize: '10px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
          labelStyle={{ color: 'var(--color-text-primary)', fontWeight: 600, marginBottom: 4 }}
          itemStyle={{ padding: 0 }}
        />
        {(['bank_a', 'bank_b', 'bank_c'] as const).map((bankId) => (
          <Area
            key={bankId}
            type="monotone"
            dataKey={bankId}
            stroke={BANK_COLORS[bankId]}
            strokeWidth={2}
            fill={`url(#grad-${bankId})`}
            name={BANK_NAMES[bankId]}
            animationDuration={800}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

function HourlyChart({ data }: { data: Record<string, unknown>[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }} barGap={1} barCategoryGap="20%">
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" opacity={0.5} />
        <XAxis
          dataKey="hour"
          tick={{ fontSize: 8, fill: 'var(--color-text-muted)' }}
          interval={2}
          tickLine={false}
          axisLine={{ stroke: 'var(--color-border-subtle)' }}
        />
        <YAxis
          tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
          width={35}
          tickFormatter={(v: number) => `${v}%`}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: '8px',
            fontSize: '10px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
          labelStyle={{ color: 'var(--color-text-primary)', fontWeight: 600, marginBottom: 4 }}
          formatter={(value: number) => [`${value}%`, '']}
        />
        {(['bank_a', 'bank_b', 'bank_c'] as const).map((bankId) => (
          <Bar
            key={bankId}
            dataKey={bankId}
            fill={BANK_COLORS[bankId]}
            radius={[2, 2, 0, 0]}
            name={BANK_NAMES[bankId]}
            animationDuration={800}
            opacity={0.85}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function MerchantChart({ data }: { data: Record<string, unknown>[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 5, right: 10, left: 5, bottom: 5 }}
        barGap={1}
        barCategoryGap="15%"
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" opacity={0.5} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={{ stroke: 'var(--color-border-subtle)' }}
          tickFormatter={(v: number) => `${v}%`}
        />
        <YAxis
          type="category"
          dataKey="category"
          tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
          width={80}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: '8px',
            fontSize: '10px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
          labelStyle={{ color: 'var(--color-text-primary)', fontWeight: 600, marginBottom: 4, textTransform: 'capitalize' }}
          formatter={(value: number) => [`${value}%`, '']}
        />
        <Legend content={() => null} />
        {(['bank_a', 'bank_b', 'bank_c'] as const).map((bankId) => (
          <Bar
            key={bankId}
            dataKey={bankId}
            fill={BANK_COLORS[bankId]}
            radius={[0, 3, 3, 0]}
            name={BANK_NAMES[bankId]}
            animationDuration={800}
            opacity={0.85}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
