import { useState } from 'react';
import { useRegisteredClients } from '../api/queries';
import type { ClientCapabilityItem } from '../api/types';

export default function CoordinatorPage() {
  const { data: clients, isLoading, error, refetch } = useRegisteredClients();
  const [selectedBank, setSelectedBank] = useState<string | null>(null);

  const onlineCount = clients?.filter(c => c.status === 'ONLINE').length ?? 0;
  const offlineCount = clients?.filter(c => c.status === 'OFFLINE').length ?? 0;
  const cudaCount = clients?.filter(c => c.hardware_type === 'cuda').length ?? 0;

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">🛰️ Federated Coordinator Suite</h1>
          <p className="page-subtitle">
            Dynamic client registry, live heartbeat monitoring, hardware-aware parameter negotiation
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => refetch()}>
          🔄 Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-4" style={{ marginBottom: '2rem' }}>
        <div className="card" style={{ borderLeft: '4px solid #10b981' }}>
          <div className="card-body" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#10b981' }}>{onlineCount}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              🟢 Online Clients
            </div>
          </div>
        </div>
        <div className="card" style={{ borderLeft: '4px solid #ef4444' }}>
          <div className="card-body" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ef4444' }}>{offlineCount}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              🔴 Offline / Timed Out
            </div>
          </div>
        </div>
        <div className="card" style={{ borderLeft: '4px solid #8b5cf6' }}>
          <div className="card-body" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#8b5cf6' }}>{cudaCount}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              ⚡ GPU-Accelerated
            </div>
          </div>
        </div>
        <div className="card" style={{ borderLeft: '4px solid #3b82f6' }}>
          <div className="card-body" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#3b82f6' }}>{clients?.length ?? 0}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              📋 Total Registered
            </div>
          </div>
        </div>
      </div>

      {/* Client Registry Table */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div className="card-header">
          <h3 className="card-title">📡 Live Client Registry</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Auto-refreshes every 5s via heartbeat
          </span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {isLoading && (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              Loading client registry...
            </div>
          )}
          {error && (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#ef4444' }}>
              ⚠️ No clients registered yet. Bank nodes register via POST /api/v1/coordinator/handshake.
            </div>
          )}
          {!isLoading && !error && clients && clients.length === 0 && (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              No bank clients registered. Waiting for handshake connections...
            </div>
          )}
          {!isLoading && clients && clients.length > 0 && (
            <table className="table">
              <thead>
                <tr>
                  <th>Bank ID</th>
                  <th>Status</th>
                  <th>Hardware</th>
                  <th>PyTorch</th>
                  <th>Python</th>
                  <th>RAM (GB)</th>
                  <th>GPUs</th>
                  <th>Last Heartbeat</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {clients.map((client: ClientCapabilityItem) => (
                  <tr key={client.bank_id}>
                    <td>
                      <strong style={{ color: 'var(--primary)' }}>{client.bank_id}</strong>
                    </td>
                    <td>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          padding: '0.2rem 0.6rem',
                          borderRadius: '999px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          backgroundColor: client.status === 'ONLINE' ? '#10b98120' : '#ef444420',
                          color: client.status === 'ONLINE' ? '#10b981' : '#ef4444',
                        }}
                      >
                        {client.status === 'ONLINE' ? '🟢' : '🔴'} {client.status}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          padding: '0.2rem 0.6rem',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          backgroundColor: client.hardware_type === 'cuda' ? '#8b5cf620' : '#64748b20',
                          color: client.hardware_type === 'cuda' ? '#8b5cf6' : '#94a3b8',
                        }}
                      >
                        {client.hardware_type === 'cuda' ? '⚡ CUDA' : '🖥️ CPU'}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{client.pytorch_version}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{client.python_version}</td>
                    <td>{client.ram_gb.toFixed(1)}</td>
                    <td>{client.device_count}</td>
                    <td style={{ color: client.last_heartbeat_ago_seconds > 10 ? '#ef4444' : '#10b981' }}>
                      {client.last_heartbeat_ago_seconds.toFixed(1)}s ago
                    </td>
                    <td>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => setSelectedBank(selectedBank === client.bank_id ? null : client.bank_id)}
                      >
                        {selectedBank === client.bank_id ? 'Hide' : 'Negotiate'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Architecture Info */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">🏗️ Coordinator Architecture</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-3" style={{ gap: '1.5rem' }}>
            <div style={{
              padding: '1.25rem',
              background: 'var(--surface-secondary)',
              borderRadius: '12px',
              border: '1px solid var(--border)',
            }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>🤝</div>
              <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Dynamic Handshake</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Bank nodes register dynamically via REST handshake. Version compatibility check (PyTorch ≥ 2.x, Python ≥ 3.10) enforced before participation.
              </div>
            </div>
            <div style={{
              padding: '1.25rem',
              background: 'var(--surface-secondary)',
              borderRadius: '12px',
              border: '1px solid var(--border)',
            }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>💓</div>
              <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Heartbeat Monitoring</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Clients send periodic heartbeats via POST /heartbeat. Nodes missing the 15s window are automatically marked OFFLINE and excluded from rounds.
              </div>
            </div>
            <div style={{
              padding: '1.25rem',
              background: 'var(--surface-secondary)',
              borderRadius: '12px',
              border: '1px solid var(--border)',
            }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>⚖️</div>
              <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Parameter Negotiation</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                CUDA nodes ≥16GB RAM get full base parameters. CPU nodes dynamically scale batch size, epochs, and gradient accumulation steps to prevent bottlenecks.
              </div>
            </div>
          </div>

          {/* API Reference */}
          <div style={{ marginTop: '1.5rem' }}>
            <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>📋 REST API Reference</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {[
                { method: 'POST', path: '/api/v1/coordinator/handshake', desc: 'Register bank client and validate runtime compatibility' },
                { method: 'POST', path: '/api/v1/coordinator/heartbeat', desc: 'Record heartbeat ping to remain in the active registry' },
                { method: 'GET',  path: '/api/v1/coordinator/clients', desc: 'List all registered client capability profiles and statuses' },
                { method: 'GET',  path: '/api/v1/coordinator/negotiate', desc: 'Retrieve heterogeneous training parameters for a bank node' },
              ].map(({ method, path, desc }) => (
                <div key={path} style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '1rem',
                  padding: '0.75rem 1rem',
                  background: 'var(--surface-secondary)',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                }}>
                  <span style={{
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    minWidth: '40px',
                    textAlign: 'center',
                    backgroundColor: method === 'POST' ? '#3b82f620' : '#10b98120',
                    color: method === 'POST' ? '#3b82f6' : '#10b981',
                  }}>
                    {method}
                  </span>
                  <code style={{ fontFamily: 'monospace', fontSize: '0.82rem', color: 'var(--primary)', flexShrink: 0 }}>
                    {path}
                  </code>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
