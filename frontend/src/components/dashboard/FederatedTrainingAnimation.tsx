import { motion, AnimatePresence } from 'framer-motion';

interface FederatedTrainingAnimationProps {
  status: string;
  currentRound: number;
  totalRounds: number;
}

const BANK_COLORS = [
  { main: 'var(--color-accent-indigo)', light: 'var(--color-accent-indigo-light)' },
  { main: 'var(--color-accent-teal)', light: 'var(--color-accent-teal)' },
  { main: 'var(--color-accent-rose)', light: 'var(--color-accent-rose)' },
];

const BANK_LABELS = ['Bank A', 'Bank B', 'Bank C'];

const PHASE_INFO: Record<string, { label: string; description: string }> = {
  pending: { label: 'Waiting', description: 'Preparing simulation environment...' },
  generating_data: { label: 'Data Generation', description: 'Generating synthetic transaction data for each bank...' },
  training_local: { label: 'Local Training', description: 'Each bank trains independently on its own data...' },
  training_federated: { label: 'Federated Training', description: 'Banks share model updates with the central server...' },
  evaluating: { label: 'Evaluation', description: 'Comparing local vs federated model performance...' },
  completed: { label: 'Complete', description: 'Training finished! View results below.' },
  failed: { label: 'Failed', description: 'An error occurred during training.' },
};

// Bank positions in SVG: triangle layout with server in center
const BANK_POSITIONS = [
  { x: 200, y: 50 },   // Bank A - top center
  { x: 60, y: 250 },   // Bank B - bottom left
  { x: 340, y: 250 },  // Bank C - bottom right
];
const SERVER_POS = { x: 200, y: 165 };

export default function FederatedTrainingAnimation({
  status,
  currentRound,
  totalRounds,
}: FederatedTrainingAnimationProps) {
  const phase = PHASE_INFO[status] ?? PHASE_INFO.pending!;
  const progressPct = totalRounds > 0 ? (currentRound / totalRounds) * 100 : 0;

  const isFederated = status === 'training_federated';
  const isLocal = status === 'training_local';
  const isGenerating = status === 'generating_data';
  const isEvaluating = status === 'evaluating';
  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';
  const isActive = !isCompleted && !isFailed && status !== 'pending';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6 overflow-hidden"
    >
      {/* Phase Stepper */}
      <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-2">
        {['generating_data', 'training_local', 'training_federated', 'evaluating', 'completed'].map((step, idx, arr) => {
          const stepPhase = PHASE_INFO[step]!;
          const stepIdx = arr.indexOf(step);
          const currentIdx = arr.indexOf(status);
          const isDone = currentIdx > stepIdx || isCompleted;
          const isCurrent = status === step;

          return (
            <div key={step} className="flex items-center gap-1 shrink-0">
              <div className="flex flex-col items-center">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-500 ${
                    isDone
                      ? 'bg-[var(--color-status-success)] text-white'
                      : isCurrent
                        ? 'bg-[var(--color-accent-indigo)] text-white shadow-lg shadow-[var(--color-accent-indigo)]/30'
                        : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] border border-[var(--color-border)]'
                  }`}
                >
                  {isDone ? '✓' : idx + 1}
                </div>
                <span className={`text-[9px] mt-1 whitespace-nowrap ${
                  isCurrent ? 'text-[var(--color-accent-indigo-light)] font-medium' : 'text-[var(--color-text-muted)]'
                }`}>
                  {stepPhase.label}
                </span>
              </div>
              {idx < arr.length - 1 && (
                <div
                  className={`w-6 h-[2px] mb-4 transition-colors duration-500 ${
                    isDone ? 'bg-[var(--color-status-success)]' : 'bg-[var(--color-border)]'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Phase Info */}
      <AnimatePresence mode="wait">
        <motion.div
          key={status}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -5 }}
          className="text-center mb-4"
        >
          <p className="text-sm font-semibold text-[var(--color-text-primary)]">{phase.label}</p>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{phase.description}</p>
        </motion.div>
      </AnimatePresence>

      {/* Progress bar */}
      {isActive && (
        <div className="mb-6">
          <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mb-1.5">
            <span>Round {currentRound} / {totalRounds}</span>
            <span className="font-mono">{progressPct.toFixed(0)}%</span>
          </div>
          <div className="w-full h-2 bg-[var(--color-bg-elevated)] rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{
                background: 'linear-gradient(90deg, var(--color-accent-indigo), var(--color-accent-teal))',
              }}
              initial={{ width: 0 }}
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            />
          </div>
        </div>
      )}

      {/* SVG Animation */}
      <div className="relative flex justify-center">
        <svg viewBox="0 0 400 310" className="w-full max-w-md" style={{ filter: isActive ? undefined : 'grayscale(0.2)' }}>
          <defs>
            {/* Gradient for data flow */}
            <linearGradient id="flow-grad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--color-accent-indigo)" stopOpacity="0.8" />
              <stop offset="100%" stopColor="var(--color-accent-teal)" stopOpacity="0.8" />
            </linearGradient>
            {/* Glow filter */}
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Connection lines between banks and server */}
          {BANK_POSITIONS.map((pos, i) => (
            <g key={`conn-${i}`}>
              {/* Base line */}
              <line
                x1={pos.x} y1={pos.y}
                x2={SERVER_POS.x} y2={SERVER_POS.y}
                stroke="var(--color-border)"
                strokeWidth="1.5"
                strokeDasharray={isFederated || isEvaluating ? "none" : "4 4"}
                opacity={0.4}
              />

              {/* Animated flow line - bank to server (upload) */}
              {isFederated && (
                <>
                  {/* Upload flow line */}
                  <line
                    x1={pos.x} y1={pos.y}
                    x2={SERVER_POS.x} y2={SERVER_POS.y}
                    stroke={BANK_COLORS[i]!.main}
                    strokeWidth="2"
                    strokeDasharray="8 6"
                    opacity={0.7}
                    filter="url(#glow)"
                  >
                    <animate
                      attributeName="stroke-dashoffset"
                      from="28"
                      to="0"
                      dur={`${1.6 + i * 0.3}s`}
                      repeatCount="indefinite"
                    />
                  </line>
                  {/* Download flow line (reverse direction) */}
                  <line
                    x1={SERVER_POS.x} y1={SERVER_POS.y}
                    x2={pos.x} y2={pos.y}
                    stroke="var(--color-accent-teal)"
                    strokeWidth="1.5"
                    strokeDasharray="6 8"
                    opacity={0.6}
                    filter="url(#glow)"
                  >
                    <animate
                      attributeName="stroke-dashoffset"
                      from="0"
                      to="28"
                      dur={`${1.8 + i * 0.3}s`}
                      repeatCount="indefinite"
                    />
                  </line>
                </>
              )}

              {/* Animated flow line - server to bank (download, evaluating) */}
              {isEvaluating && (
                <line
                  x1={SERVER_POS.x} y1={SERVER_POS.y}
                  x2={pos.x} y2={pos.y}
                  stroke="var(--color-status-success)"
                  strokeWidth="2"
                  strokeDasharray="8 6"
                  opacity={0.8}
                  filter="url(#glow)"
                >
                  <animate
                    attributeName="stroke-dashoffset"
                    from="28"
                    to="0"
                    dur={`${1.0 + i * 0.2}s`}
                    repeatCount="indefinite"
                  />
                </line>
              )}

              {/* Completed: solid green */}
              {isCompleted && (
                <line
                  x1={pos.x} y1={pos.y}
                  x2={SERVER_POS.x} y2={SERVER_POS.y}
                  stroke="var(--color-status-success)"
                  strokeWidth="2"
                  opacity={0.6}
                />
              )}
            </g>
          ))}

          {/* Bidirectional Data packets flowing (federated phase) */}
          {isFederated && BANK_POSITIONS.map((pos, i) => (
            <g key={`packets-${i}`}>
              {/* Uplink packet (Bank -> Server) */}
              <circle r="4" fill={BANK_COLORS[i]!.main} filter="url(#glow)">
                <animateMotion
                  dur="2s"
                  repeatCount="indefinite"
                  path={`M${pos.x},${pos.y} L${SERVER_POS.x},${SERVER_POS.y}`}
                  begin={`${i * 0.3}s`}
                />
                <animate attributeName="opacity" values="1;0.2;1" dur="1s" repeatCount="indefinite" />
              </circle>
              {/* Downlink packet (Server -> Bank) */}
              <circle r="3.5" fill="var(--color-accent-teal)" filter="url(#glow)">
                <animateMotion
                  dur="2s"
                  repeatCount="indefinite"
                  path={`M${SERVER_POS.x},${SERVER_POS.y} L${pos.x},${pos.y}`}
                  begin={`${1.0 + i * 0.3}s`}
                />
                <animate attributeName="opacity" values="1;0.2;1" dur="1s" repeatCount="indefinite" />
              </circle>
            </g>
          ))}

          {/* Return packets (evaluating phase) */}
          {isEvaluating && BANK_POSITIONS.map((pos, i) => (
            <circle key={`ret-${i}`} r="4" fill="var(--color-status-success)" filter="url(#glow)">
              <animateMotion
                dur={`${1.5 + i * 0.2}s`}
                repeatCount="indefinite"
                path={`M${SERVER_POS.x},${SERVER_POS.y} L${pos.x},${pos.y}`}
              />
              <animate attributeName="opacity" values="1;0.4;1" dur="1s" repeatCount="indefinite" />
            </circle>
          ))}

          {/* Bank nodes */}
          {BANK_POSITIONS.map((pos, i) => {
            const isTrainingNow = isLocal || isFederated;
            return (
              <g key={`bank-${i}`}>
                {/* Pulse ring during activity */}
                {(isGenerating || isTrainingNow) && (
                  <circle cx={pos.x} cy={pos.y} r="28" fill="none" stroke={BANK_COLORS[i]!.main} strokeWidth="1.5" opacity="0.4">
                    <animate attributeName="r" values="28;38;28" dur="2s" repeatCount="indefinite" begin={`${i * 0.4}s`} />
                    <animate attributeName="opacity" values="0.4;0;0.4" dur="2s" repeatCount="indefinite" begin={`${i * 0.4}s`} />
                  </circle>
                )}

                {/* Bank circle */}
                <circle
                  cx={pos.x} cy={pos.y} r="26"
                  fill="var(--color-bg-card)"
                  stroke={isCompleted ? 'var(--color-status-success)' : isFailed ? 'var(--color-status-error)' : BANK_COLORS[i]!.main}
                  strokeWidth="2.5"
                  filter={isTrainingNow ? 'url(#glow)' : undefined}
                />

                {/* Bank icon (building) */}
                <text x={pos.x} y={pos.y + 1} textAnchor="middle" dominantBaseline="central" fontSize="18">
                  🏦
                </text>

                {/* Bank label */}
                <text
                  x={pos.x} y={pos.y + 42}
                  textAnchor="middle"
                  fontSize="11"
                  fontWeight="600"
                  fill="var(--color-text-secondary)"
                >
                  {BANK_LABELS[i]}
                </text>

                {/* Training indicator */}
                {isLocal && (
                  <g>
                    <circle cx={pos.x + 18} cy={pos.y - 18} r="8" fill="var(--color-accent-indigo)" />
                    <text x={pos.x + 18} y={pos.y - 17} textAnchor="middle" dominantBaseline="central" fontSize="8" fill="white">⚙</text>
                    <animateTransform
                      attributeName="transform"
                      type="rotate"
                      from={`0 ${pos.x + 18} ${pos.y - 18}`}
                      to={`360 ${pos.x + 18} ${pos.y - 18}`}
                      dur="3s"
                      repeatCount="indefinite"
                    />
                  </g>
                )}
              </g>
            );
          })}

          {/* Central aggregation server */}
          <g>
            {/* Server pulse */}
            {isFederated && (
              <circle cx={SERVER_POS.x} cy={SERVER_POS.y} r="30" fill="none" stroke="url(#flow-grad)" strokeWidth="1.5" opacity="0.4">
                <animate attributeName="r" values="30;42;30" dur="2.5s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.4;0;0.4" dur="2.5s" repeatCount="indefinite" />
              </circle>
            )}

            {/* Completed burst */}
            {isCompleted && (
              <>
                <circle cx={SERVER_POS.x} cy={SERVER_POS.y} r="30" fill="none" stroke="var(--color-status-success)" strokeWidth="2" opacity="0.3">
                  <animate attributeName="r" values="30;50;30" dur="3s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.3;0;0.3" dur="3s" repeatCount="indefinite" />
                </circle>
              </>
            )}

            {/* Server circle */}
            <circle
              cx={SERVER_POS.x} cy={SERVER_POS.y} r="28"
              fill="var(--color-bg-card)"
              stroke={isCompleted ? 'var(--color-status-success)' : isFederated ? 'url(#flow-grad)' : 'var(--color-border)'}
              strokeWidth={isFederated || isCompleted ? 3 : 2}
              filter={isFederated ? 'url(#glow)' : undefined}
            />

            {/* Server icon */}
            <text x={SERVER_POS.x} y={SERVER_POS.y + 1} textAnchor="middle" dominantBaseline="central" fontSize="20">
              {isCompleted ? '✅' : '🖥️'}
            </text>

            {/* Server label */}
            <text
              x={SERVER_POS.x} y={SERVER_POS.y + 46}
              textAnchor="middle"
              fontSize="10"
              fontWeight="600"
              fill="var(--color-text-muted)"
            >
              Aggregation Server
            </text>
          </g>
        </svg>
      </div>

      {/* Round counter for federated phase */}
      {isFederated && currentRound > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center mt-2"
        >
          <span className="text-xs font-mono px-3 py-1 rounded-full bg-[var(--color-accent-indigo)]/10 text-[var(--color-accent-indigo-light)]">
            Communication Round {currentRound}
          </span>
        </motion.div>
      )}
    </motion.div>
  );
}
