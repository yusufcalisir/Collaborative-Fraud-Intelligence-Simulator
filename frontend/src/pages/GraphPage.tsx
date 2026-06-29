import { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useEntities, useGraph, useGraphStats } from '../api/queries';
import { ENTITY_TYPE_COLORS, BANK_NAMES } from '../api/types';
import type { Entity } from '../api/types';

export default function GraphPage() {
  const [selectedEntityId, setSelectedEntityId] = useState<string | undefined>();
  const [depth, setDepth] = useState(2);
  const [searchQuery, setSearchQuery] = useState('');
  const { data: entities } = useEntities();
  const { data: graphData } = useGraph(selectedEntityId, depth);
  const { data: graphStats } = useGraphStats();

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Update nodes/edges when graph data changes
  useMemo(() => {
    if (graphData) {
      setNodes(graphData.nodes as unknown as Node[]);
      setEdges(graphData.edges as unknown as Edge[]);
    }
  }, [graphData, setNodes, setEdges]);

  const filteredEntities = useMemo(() => {
    if (!entities) return [];
    if (!searchQuery) return entities.slice(0, 20);
    return entities.filter(
      (e) =>
        e.display_label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.privacy_id.toLowerCase().includes(searchQuery.toLowerCase()),
    ).slice(0, 20);
  }, [entities, searchQuery]);

  const onNodeClick = useCallback((_: unknown, node: Node) => {
    setSelectedEntityId(node.id);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-2xl font-bold gradient-text mb-1">
          Entity Relationship Graph
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] max-w-2xl">
          Interactive graph of entities connected by transactions, shared devices, and cross-institution
          intelligence. Clusters often indicate fraud rings.
        </p>
      </motion.div>

      <div className="flex flex-col-reverse lg:grid lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="space-y-4">
          {/* Graph Stats */}
          {graphStats && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="glass-card p-4"
            >
              <h3 className="text-xs font-bold uppercase text-[var(--color-text-muted)] mb-3">
                Graph Stats
              </h3>
              <div className="grid grid-cols-2 gap-3 text-center">
                {[
                  { label: 'Nodes', value: graphStats.total_nodes },
                  { label: 'Edges', value: graphStats.total_edges },
                  { label: 'Clusters', value: graphStats.cluster_count },
                  { label: 'Types', value: Object.keys(graphStats.nodes_by_type).length },
                ].map((stat) => (
                  <div key={stat.label}>
                    <div className="text-lg font-bold">{stat.value}</div>
                    <div className="text-[10px] uppercase text-[var(--color-text-muted)]">{stat.label}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Depth Control */}
          <div className="glass-card p-4">
            <h3 className="text-xs font-bold uppercase text-[var(--color-text-muted)] mb-2">
              Traversal Depth
            </h3>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="1"
                max="4"
                value={depth}
                onChange={(e) => setDepth(parseInt(e.target.value))}
                className="flex-1 accent-[var(--color-primary)]"
              />
              <span className="text-sm font-mono font-bold w-6">{depth}</span>
            </div>
          </div>

          {/* Entity Search */}
          <div className="glass-card p-4">
            <h3 className="text-xs font-bold uppercase text-[var(--color-text-muted)] mb-2">
              Search Entities
            </h3>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by label or ID..."
              className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--color-surface-alt)] border border-[var(--color-border)] text-[var(--color-text)]"
            />

            <div className="mt-3 space-y-1 max-h-64 overflow-y-auto">
              {filteredEntities.map((entity) => (
                <EntityListItem
                  key={entity.id}
                  entity={entity}
                  isSelected={selectedEntityId === entity.id}
                  onClick={() => setSelectedEntityId(entity.id)}
                />
              ))}
              {!filteredEntities.length && (
                <p className="text-xs text-[var(--color-text-muted)] py-2">
                  {entities?.length ? 'No matches' : 'No entities. Run a scenario first.'}
                </p>
              )}
            </div>
          </div>

          {/* Legend */}
          <div className="glass-card p-4">
            <h3 className="text-xs font-bold uppercase text-[var(--color-text-muted)] mb-2">
              Entity Types
            </h3>
            <div className="space-y-1.5">
              {Object.entries(ENTITY_TYPE_COLORS).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2 text-xs">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="capitalize">{type.replace('_', ' ')}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Graph Canvas */}
        <div className="lg:col-span-3">
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card overflow-hidden h-[450px] sm:h-[550px] lg:h-[600px]"
          >
            {!selectedEntityId ? (
              <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
                <div className="text-center">
                  <div className="text-4xl mb-3">🕸️</div>
                  <p className="text-lg font-semibold mb-1">Select an entity</p>
                  <p className="text-sm">Choose an entity from the sidebar to explore its relationship graph</p>
                </div>
              </div>
            ) : !graphData?.nodes.length ? (
              <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
                <div className="text-center">
                  <div className="text-4xl mb-3">📊</div>
                  <p>No graph data for this entity</p>
                </div>
              </div>
            ) : (
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                fitView
                proOptions={{ hideAttribution: true }}
                style={{ background: 'transparent' }}
              >
                <Background color="var(--color-border)" gap={20} size={1} />
                <Controls
                  showInteractive={false}
                  style={{
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '8px',
                  }}
                />
                <MiniMap
                  style={{
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '8px',
                  }}
                  maskColor="rgba(0,0,0,0.5)"
                />
              </ReactFlow>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}

function EntityListItem({
  entity,
  isSelected,
  onClick,
}: {
  entity: Entity;
  isSelected: boolean;
  onClick: () => void;
}) {
  const color = ENTITY_TYPE_COLORS[entity.entity_type] || '#6b7280';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${
        isSelected
          ? 'bg-[var(--color-primary)]/20 border border-[var(--color-primary)]/40'
          : 'hover:bg-[var(--color-surface-alt)]'
      }`}
    >
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
        <span className="font-mono font-semibold">{entity.display_label}</span>
        {entity.alert_count > 0 && (
          <span className="ml-auto px-1 py-0.5 bg-red-500/20 text-red-400 rounded text-[9px]">
            {entity.alert_count}
          </span>
        )}
      </div>
      <div className="text-[10px] text-[var(--color-text-muted)] ml-4">
        {BANK_NAMES[entity.bank_id] || entity.bank_id} • {entity.risk_level}
      </div>
    </button>
  );
}
