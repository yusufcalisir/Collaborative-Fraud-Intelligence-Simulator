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

      {/* Controls and Stats Row (Top) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Graph Stats */}
        {graphStats ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-4 flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold uppercase text-[var(--color-text-muted)]">
                Graph Stats
              </h3>
              {graphStats.database_backend && (
                <span
                  className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wide ${
                    graphStats.database_backend.toLowerCase().includes('neo4j')
                      ? 'bg-[#008CC1]/20 text-[#008CC1]'
                      : graphStats.database_backend.toLowerCase().includes('memgraph')
                      ? 'bg-purple-500/20 text-purple-400'
                      : 'bg-[var(--color-surface-alt)] text-[var(--color-text-muted)]'
                  }`}
                >
                  {graphStats.database_backend}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3 text-center my-auto">
              {[
                { label: 'Nodes', value: graphStats.total_nodes },
                { label: 'Edges', value: graphStats.total_edges },
                { label: 'Clusters', value: graphStats.cluster_count },
                { label: 'Types', value: Object.keys(graphStats.nodes_by_type).length },
              ].map((stat) => (
                <div key={stat.label}>
                  <div className="text-base font-bold font-mono">{stat.value}</div>
                  <div className="text-[9px] uppercase text-[var(--color-text-muted)]">{stat.label}</div>
                </div>
              ))}
            </div>
          </motion.div>
        ) : (
          <div className="glass-card p-4 h-28 animate-pulse" />
        )}


        {/* Depth Control */}
        <div className="glass-card p-4 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase text-[var(--color-text-muted)] mb-2">
              Traversal Depth
            </h3>
            <p className="text-[10px] text-[var(--color-text-muted)] mb-3">
              Control how many transaction hops to display from the selected node.
            </p>
          </div>
          <div className="flex items-center gap-3 mt-auto">
            <input
              type="range"
              min="1"
              max="4"
              value={depth}
              onChange={(e) => setDepth(parseInt(e.target.value))}
              className="flex-1 accent-[var(--color-primary)]"
            />
            <span className="text-sm font-mono font-bold w-6 text-right">{depth}</span>
          </div>
        </div>

        {/* Entity Search */}
        <div className="glass-card p-4 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase text-[var(--color-text-muted)] mb-2">
              Search & Filter
            </h3>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search label or ID..."
              className="w-full px-3 py-1.5 text-xs rounded-lg bg-[var(--color-surface-alt)] border border-[var(--color-border)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent-indigo)]"
            />
          </div>
          <div className="mt-2 space-y-1 max-h-24 overflow-y-auto pr-1">
            {filteredEntities.map((entity) => (
              <EntityListItem
                key={entity.id}
                entity={entity}
                isSelected={selectedEntityId === entity.id}
                onClick={() => setSelectedEntityId(entity.id)}
              />
            ))}
            {!filteredEntities.length && (
              <p className="text-[10px] text-[var(--color-text-muted)] py-1">
                {entities?.length ? 'No matches' : 'No entities. Run simulation first.'}
              </p>
            )}
          </div>
        </div>

        {/* Legend */}
        <div className="glass-card p-4 flex flex-col justify-between">
          <h3 className="text-xs font-bold uppercase text-[var(--color-text-muted)] mb-2">
            Entity Types Legend
          </h3>
          <div className="grid grid-cols-2 gap-x-2 gap-y-1.5 my-auto">
            {Object.entries(ENTITY_TYPE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5 text-[10px]">
                <div
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className="capitalize truncate">{type.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Graph Canvas (Bottom) */}
      <div className="w-full">
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-card overflow-hidden h-[450px] sm:h-[550px] lg:h-[600px]"
        >
          {!selectedEntityId ? (
            <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
              <div className="text-center p-6">
                <div className="text-4xl mb-3 animate-pulse">🕸️</div>
                <p className="text-lg font-semibold mb-1">Select an Entity to Start</p>
                <p className="text-sm max-w-md">
                  Choose a customer, device, or merchant from the search box above to explore resolved connections and cross-bank clusters.
                </p>
              </div>
            </div>
          ) : !graphData?.nodes.length ? (
            <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
              <div className="text-center p-6">
                <div className="text-4xl mb-3">📊</div>
                <p className="text-lg font-semibold mb-1">No Relationships Found</p>
                <p className="text-sm">This entity has no registered transaction hops in the network graph.</p>
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
