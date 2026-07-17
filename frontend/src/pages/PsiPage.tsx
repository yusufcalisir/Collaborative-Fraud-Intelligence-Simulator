import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useRunPSI } from '../api/queries';
import { BANK_NAMES } from '../api/types';

// Helper to normalize and calculate shingles in JS for the playground
function getNormalizedAndShingles(text: string): { normalized: string; shingles: string[] } {
  if (!text) return { normalized: '', shingles: [] };
  // Unicode NFC standardization, lowercasing, and diacritic stripping
  let norm = text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  
  const shingles: string[] = [];
  if (norm.length < 3) {
    if (norm) shingles.push(norm);
  } else {
    for (let i = 0; i < norm.length - 2; i++) {
      shingles.push(norm.slice(i, i + 3));
    }
  }
  return { normalized: norm, shingles: Array.from(new Set(shingles)) };
}

// Simple JS Hash to simulate MinHashing locally
function computeLocalMinHash(shingles: string[], index: number): number {
  if (shingles.length === 0) return 0;
  let minVal = Infinity;
  for (const s of shingles) {
    const salted = `${s}:${index}`;
    let hash = 0;
    for (let i = 0; i < salted.length; i++) {
      hash = (hash << 5) - hash + salted.charCodeAt(i);
      hash |= 0;
    }
    const val = Math.abs(hash);
    if (val < minVal) {
      minVal = val;
    }
  }
  return minVal % 1000000;
}

export default function PsiPage() {
  const [bankA, setBankA] = useState('bank_a');
  const [bankB, setBankB] = useState('bank_b');
  const [entityType, setEntityType] = useState('customer');
  const [enableFuzzy, setEnableFuzzy] = useState(false);
  const [fuzzyThreshold, setFuzzyThreshold] = useState(3);
  const [enableTee, setEnableTee] = useState(false);

  // Playground state
  const [playName1, setPlayName1] = useState('Yusuf Çalışır');
  const [playName2, setPlayName2] = useState('Yusuf Calisir');

  // Queries
  const runPsiMutation = useRunPSI();

  // Run the PSI protocol
  const handleRunPSI = () => {
    runPsiMutation.mutate({
      bank_a_id: bankA,
      bank_b_id: bankB,
      entity_type: entityType,
      enable_fuzzy: enableFuzzy,
      fuzzy_threshold: fuzzyThreshold,
    });
  };

  // Compute LSH details for the playground
  const playgroundDetails = useMemo(() => {
    const res1 = getNormalizedAndShingles(playName1);
    const res2 = getNormalizedAndShingles(playName2);

    const sig1: number[] = [];
    const sig2: number[] = [];
    for (let i = 0; i < 16; i++) {
      sig1.push(computeLocalMinHash(res1.shingles, i));
      sig2.push(computeLocalMinHash(res2.shingles, i));
    }

    let matches = 0;
    for (let i = 0; i < 16; i++) {
      if (sig1[i] === sig2[i]) matches++;
    }
    const estimatedJaccard = sig1.length > 0 ? matches / sig1.length : 0;

    return {
      norm1: res1.normalized,
      norm2: res2.normalized,
      shingles1: res1.shingles,
      shingles2: res2.shingles,
      sig1,
      sig2,
      jaccard: estimatedJaccard,
    };
  }, [playName1, playName2]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-2xl font-bold gradient-text mb-1">
          Private Set Intersection & Fuzzy Matching
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] max-w-3xl">
          Execute privacy-preserving cryptographic overlap calculations between banking institutions.
          Compare deterministic database exact-hashing or switch to probabilistic Fuzzy PSI and MinHash Locality-Sensitive Hashing (LSH) for compliance-grade fuzzy matching.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel: Protocol Controls */}
        <div className="space-y-6 lg:col-span-1">
          <div className="glass-card p-5 space-y-4">
            <h3 className="text-sm font-bold uppercase text-[var(--color-text-muted)] tracking-wider">
              PSI Configuration
            </h3>

            {/* Institution Selectors */}
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase text-[var(--color-text-muted)] block mb-1">
                  Primary Institution (Bank A)
                </label>
                <select
                  value={bankA}
                  onChange={(e) => setBankA(e.target.value)}
                  className="w-full bg-[var(--color-bg-dark)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-blue)]"
                >
                  {Object.entries(BANK_NAMES).map(([id, name]) => (
                    <option key={id} value={id}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] uppercase text-[var(--color-text-muted)] block mb-1">
                  Partner Institution (Bank B)
                </label>
                <select
                  value={bankB}
                  onChange={(e) => setBankB(e.target.value)}
                  className="w-full bg-[var(--color-bg-dark)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-blue)]"
                >
                  {Object.entries(BANK_NAMES).map(([id, name]) => (
                    <option key={id} value={id}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Entity Filter */}
            <div>
              <label className="text-[10px] uppercase text-[var(--color-text-muted)] block mb-1">
                Entity Domain Type
              </label>
              <select
                value={entityType}
                onChange={(e) => setEntityType(e.target.value)}
                className="w-full bg-[var(--color-bg-dark)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-blue)]"
              >
                <option value="customer">Customers (Fuzzy Resolution Enabled)</option>
                <option value="merchant">Merchants</option>
                <option value="device">Devices</option>
                <option value="card">Credit Cards</option>
              </select>
            </div>

            {/* Toggles */}
            <div className="border-t border-[var(--color-border)] pt-3 space-y-2">
              <label className="flex items-center space-x-2.5 cursor-pointer py-1 select-none">
                <input
                  type="checkbox"
                  checked={enableFuzzy}
                  onChange={(e) => setEnableFuzzy(e.target.checked)}
                  className="rounded border-[var(--color-border)] bg-[var(--color-bg-dark)] text-[var(--color-accent-blue)] focus:ring-0 focus:ring-offset-0"
                />
                <div>
                  <span className="text-xs font-semibold text-[var(--color-text-primary)]">
                    Enable Fuzzy PSI
                  </span>
                  <p className="text-[9px] text-[var(--color-text-muted)]">
                    Match entities on multi-attribute threshold overlap (phone, email, surname...)
                  </p>
                </div>
              </label>

              {enableFuzzy && (
                <div className="pl-6 animate-fadeIn">
                  <label className="text-[9px] uppercase text-[var(--color-text-muted)] block mb-1">
                    Matching Attributes Threshold ({fuzzyThreshold}/5)
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={fuzzyThreshold}
                    onChange={(e) => setFuzzyThreshold(parseInt(e.target.value))}
                    className="w-full h-1 bg-[var(--color-bg-dark)] rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-[8px] text-[var(--color-text-muted)] mt-1">
                    <span>1 (Relaxed)</span>
                    <span>3 (Standard)</span>
                    <span>5 (Exact)</span>
                  </div>
                </div>
              )}

              <label className="flex items-center space-x-2.5 cursor-pointer py-1 select-none">
                <input
                  type="checkbox"
                  checked={enableTee}
                  onChange={(e) => setEnableTee(e.target.checked)}
                  className="rounded border-[var(--color-border)] bg-[var(--color-bg-dark)] text-[var(--color-accent-blue)] focus:ring-0 focus:ring-offset-0"
                />
                <div>
                  <span className="text-xs font-semibold text-[var(--color-text-primary)]">
                    Hardware TEE Acceleration (SGX)
                  </span>
                  <p className="text-[9px] text-[var(--color-text-muted)]">
                    Simulate secure enclaves to bypass modular exponentiation overhead
                  </p>
                </div>
              </label>
            </div>

            <button
              onClick={handleRunPSI}
              disabled={runPsiMutation.isPending || bankA === bankB}
              className="w-full bg-gradient-to-r from-[var(--color-accent-blue)] to-[var(--color-accent-purple)] text-white font-bold py-2 rounded-md text-xs hover:shadow-lg transition-shadow duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {runPsiMutation.isPending ? 'Computing Private Intersection...' : 'Run PSI Protocol'}
            </button>

            {bankA === bankB && (
              <p className="text-[9px] text-center text-red-400 mt-1">
                Selected institutions must be different.
              </p>
            )}
          </div>

          {/* Protocol Analytics */}
          {runPsiMutation.data && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-card p-5 space-y-4 border border-[var(--color-accent-blue-light)]"
            >
              <h3 className="text-sm font-bold uppercase text-[var(--color-text-primary)] flex items-center gap-1.5">
                <span>⚡</span> Protocol Performance
              </h3>
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="bg-[var(--color-bg-dark)] p-2.5 rounded border border-[var(--color-border)]">
                  <div className="text-sm font-mono font-bold text-[var(--color-accent-blue)]">
                    {runPsiMutation.data.stats.computation_time_ms} ms
                  </div>
                  <div className="text-[8px] uppercase text-[var(--color-text-muted)] mt-1">
                    Calc Latency
                  </div>
                </div>

                <div className="bg-[var(--color-bg-dark)] p-2.5 rounded border border-[var(--color-border)]">
                  <div className="text-sm font-mono font-bold text-[var(--color-accent-purple)]">
                    {runPsiMutation.data.stats.data_exchanged_bytes.toLocaleString()} B
                  </div>
                  <div className="text-[8px] uppercase text-[var(--color-text-muted)] mt-1">
                    Exchanged Payload
                  </div>
                </div>
              </div>

              <div className="space-y-1.5 text-[10px] text-[var(--color-text-muted)]">
                <div className="flex justify-between">
                  <span>DH Exponent Bit-Length:</span>
                  <span className="font-mono text-[var(--color-text-primary)]">
                    {runPsiMutation.data.stats.prime_bit_length} bits
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Enclave Verification (TEE):</span>
                  <span
                    className={`font-semibold ${
                      runPsiMutation.data.stats.enclave_execution ? 'text-emerald-400' : 'text-amber-400'
                    }`}
                  >
                    {runPsiMutation.data.stats.enclave_execution ? 'VERIFIED (SGX)' : 'Disabled'}
                  </span>
                </div>
                {runPsiMutation.data.stats.mrenclave && (
                  <div className="border-t border-[var(--color-border)] pt-1.5 mt-1.5 space-y-1 text-[8px]">
                    <div className="flex justify-between">
                      <span>MRENCLAVE:</span>
                      <span className="font-mono text-[var(--color-text-primary)] truncate max-w-[140px]">
                        {runPsiMutation.data.stats.mrenclave}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>MRSIGNER:</span>
                      <span className="font-mono text-[var(--color-text-primary)] truncate max-w-[140px]">
                        {runPsiMutation.data.stats.mrsigner}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </div>

        {/* Right Panel: Visualization & Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Cryptographic Workflow Animation (Interactive) */}
          <div className="glass-card p-5 space-y-4">
            <h3 className="text-sm font-bold uppercase text-[var(--color-text-muted)] tracking-wider">
              Cryptographic Execution Model
            </h3>
            
            <div className="relative border border-[var(--color-border)] rounded-md p-4 bg-[var(--color-bg-dark)] overflow-hidden">
              <div className="grid grid-cols-3 gap-2 text-center text-[10px] text-[var(--color-text-muted)]">
                <div className="space-y-1">
                  <div className="p-2 rounded bg-opacity-10 border border-dashed border-gray-600 bg-gray-500 text-[var(--color-text-primary)]">
                    Local Salting
                  </div>
                  <div className="text-[8px]">Convert attributes to deterministic strings & hashes.</div>
                </div>

                <div className="space-y-1">
                  <div className="p-2 rounded bg-opacity-10 border border-dashed border-gray-600 bg-gray-500 text-[var(--color-text-primary)]">
                    Pass 1 Exponent
                  </div>
                  <div className="text-[8px]">Encrypt with locally-stored KMS private scalar.</div>
                </div>

                <div className="space-y-1">
                  <div className="p-2 rounded bg-opacity-10 border border-dashed border-gray-600 bg-gray-500 text-[var(--color-text-primary)]">
                    Cross Exponent
                  </div>
                  <div className="text-[8px]">Exchange & encrypt with partner key. Match overlap.</div>
                </div>
              </div>

              {/* Dynamic status lines */}
              <div className="mt-4 flex items-center justify-center gap-4 text-[9px] text-[var(--color-text-muted)]">
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-[var(--color-accent-blue)] animate-pulse" />
                  <span>Bank A Key Exponent: {runPsiMutation.data ? 'active' : 'idle'}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-[var(--color-accent-purple)] animate-pulse" />
                  <span>Bank B Key Exponent: {runPsiMutation.data ? 'active' : 'idle'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Matches List */}
          <div className="glass-card p-5 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold uppercase text-[var(--color-text-muted)] tracking-wider">
                Intersection Results
              </h3>
              {runPsiMutation.data && (
                <span className="text-[10px] font-mono text-[var(--color-accent-blue)]">
                  {runPsiMutation.data.matches.length} Matches Found
                </span>
              )}
            </div>

            {runPsiMutation.isIdle && (
              <div className="p-8 text-center text-xs text-[var(--color-text-muted)]">
                Click "Run PSI Protocol" to start cryptographic computations.
              </div>
            )}

            {runPsiMutation.data && runPsiMutation.data.matches.length === 0 && (
              <div className="p-8 text-center text-xs text-[var(--color-text-muted)]">
                No matching entities found between institutions in this subset.
              </div>
            )}

            {runPsiMutation.data && runPsiMutation.data.matches.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--color-border)] text-[9px] uppercase tracking-wider text-[var(--color-text-muted)]">
                      <th className="py-2.5 font-bold">Privacy Hash</th>
                      <th className="py-2.5 font-bold">Entity Type</th>
                      <th className="py-2.5 font-bold">Label (Bank A)</th>
                      <th className="py-2.5 font-bold">Label (Bank B)</th>
                      <th className="py-2.5 font-bold text-center">Risk A / B</th>
                      {enableFuzzy && <th className="py-2.5 font-bold">Overlap</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {runPsiMutation.data.matches.map((m, idx) => (
                      <tr
                        key={idx}
                        className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-dark)] bg-opacity-40 transition-colors"
                      >
                        <td className="py-3 font-mono font-bold text-[var(--color-accent-blue-light)]">
                          {m.privacy_hash}
                        </td>
                        <td className="py-3 capitalize">{m.entity_type}</td>
                        <td className="py-3">{m.display_label_a}</td>
                        <td className="py-3">{m.display_label_b}</td>
                        <td className="py-3 text-center">
                          <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${
                            m.risk_level_a === 'critical' || m.risk_level_a === 'high' ? 'bg-red-950 text-red-400' : 'bg-gray-800 text-gray-400'
                          }`}>
                            {m.risk_level_a}
                          </span>
                          <span className="text-gray-600 mx-1">/</span>
                          <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${
                            m.risk_level_b === 'critical' || m.risk_level_b === 'high' ? 'bg-red-950 text-red-400' : 'bg-gray-800 text-gray-400'
                          }`}>
                            {m.risk_level_b}
                          </span>
                        </td>
                        {enableFuzzy && (
                          <td className="py-3">
                            <div className="flex flex-col gap-0.5">
                              <span className="text-[10px] font-mono text-[var(--color-accent-purple-light)]">
                                {Math.round((m.similarity_score || 0) * 100)}% Match
                              </span>
                              <span className="text-[8px] text-[var(--color-text-muted)] truncate max-w-[120px]">
                                {m.matched_attributes?.join(', ')}
                              </span>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* LSH MinHash Playground section */}
      <div className="glass-card p-5 space-y-4">
        <h3 className="text-sm font-bold uppercase text-[var(--color-text-primary)] flex items-center gap-1.5">
          <span>👤</span> LSH MinHash Fuzzy Similarity Playground
        </h3>
        <p className="text-xs text-[var(--color-text-muted)]">
          Locality-Sensitive Hashing (LSH) allows banks to detect name duplicates fuzzily by comparing character n-grams signatures.
          Input two spellings below to see standardization, computed character 3-gram shingles, and approximated Jaccard similarity.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-[9px] uppercase text-[var(--color-text-muted)] block mb-1">
              Raw Input Spelling 1
            </label>
            <input
              type="text"
              value={playName1}
              onChange={(e) => setPlayName1(e.target.value)}
              className="w-full bg-[var(--color-bg-dark)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-blue)]"
              placeholder="e.g. Yusuf Çalışır"
            />
          </div>

          <div>
            <label className="text-[9px] uppercase text-[var(--color-text-muted)] block mb-1">
              Raw Input Spelling 2
            </label>
            <input
              type="text"
              value={playName2}
              onChange={(e) => setPlayName2(e.target.value)}
              className="w-full bg-[var(--color-bg-dark)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-blue)]"
              placeholder="e.g. Yusuf Calisir"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 pt-3 border-t border-[var(--color-border)]">
          {/* String 1 breakdown */}
          <div className="space-y-2 bg-[var(--color-bg-dark)] bg-opacity-40 p-3.5 rounded border border-[var(--color-border)]">
            <div className="text-[9px] uppercase text-[var(--color-text-muted)]">Spelling 1 Metadata</div>
            <div className="text-xs">
              <span className="text-[10px] text-[var(--color-text-muted)] block">Standardized:</span>
              <span className="font-mono font-semibold text-[var(--color-accent-blue)]">{playgroundDetails.norm1 || 'none'}</span>
            </div>
            <div>
              <span className="text-[10px] text-[var(--color-text-muted)] block mb-1">3-Grams Shingles:</span>
              <div className="flex flex-wrap gap-1">
                {playgroundDetails.shingles1.map((s, i) => (
                  <span key={i} className="text-[8px] font-mono px-1.5 py-0.5 bg-gray-800 rounded">
                    "{s}"
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* String 2 breakdown */}
          <div className="space-y-2 bg-[var(--color-bg-dark)] bg-opacity-40 p-3.5 rounded border border-[var(--color-border)]">
            <div className="text-[9px] uppercase text-[var(--color-text-muted)]">Spelling 2 Metadata</div>
            <div className="text-xs">
              <span className="text-[10px] text-[var(--color-text-muted)] block">Standardized:</span>
              <span className="font-mono font-semibold text-[var(--color-accent-blue)]">{playgroundDetails.norm2 || 'none'}</span>
            </div>
            <div>
              <span className="text-[10px] text-[var(--color-text-muted)] block mb-1">3-Grams Shingles:</span>
              <div className="flex flex-wrap gap-1">
                {playgroundDetails.shingles2.map((s, i) => (
                  <span key={i} className="text-[8px] font-mono px-1.5 py-0.5 bg-gray-800 rounded">
                    "{s}"
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Jaccard similarity output */}
          <div className="flex flex-col justify-center items-center p-3.5 rounded border border-[var(--color-accent-blue)] bg-gradient-to-b from-[var(--color-bg-dark)] to-slate-900 text-center">
            <span className="text-[10px] uppercase text-[var(--color-text-muted)]">Estimated Jaccard Similarity</span>
            <div className="text-3xl font-mono font-bold gradient-text my-2">
              {Math.round(playgroundDetails.jaccard * 100)}%
            </div>
            <span className="text-[9px] text-[var(--color-text-muted)]">
              MinHash Signature Match: {playgroundDetails.sig1.filter((x, i) => x === playgroundDetails.sig2[i]).length} / 16 hashes
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
