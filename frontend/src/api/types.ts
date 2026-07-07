/** API response types matching the FastAPI Pydantic schemas. */

export interface SimulationConfig {
  num_rounds: number;
  local_epochs: number;
  learning_rate: number;
  batch_size: number;
  min_clients_per_round: number;
  enable_latency_simulation: boolean;
  latency_min_ms: number;
  latency_max_ms: number;
  enable_dropout_simulation: boolean;
  dropout_probability: number;
  enable_reconnect_simulation: boolean;
  privacy_mechanism: 'none' | 'differential_privacy' | 'secure_aggregation' | 'both';
  dp_epsilon: number;
  dp_delta: number;
  dp_max_grad_norm: number;
  dp_mode: 'post_hoc' | 'opacus';
  bank_a_transactions: number;
  bank_b_transactions: number;
  bank_c_transactions: number;
  aggregation_method: 'fed_avg_weighted' | 'fed_avg' | 'krum' | 'coordinate_wise_median';
  enable_poisoning_simulation: boolean;
  poisoning_bank_id: string;
  poisoning_scale: number;
}

export interface EvaluationMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  auc_roc: number;
  loss: number;
  confusion_matrix: number[][];
  roc_fpr: number[];
  roc_tpr: number[];
  roc_thresholds: number[];
  feature_importance: Record<string, number>;
}

export interface DataProfile {
  bank_name: string;
  num_transactions: number;
  fraud_ratio: number;
  mean_transaction_amount: number;
  std_transaction_amount: number;
  top_merchant_categories: string[];
  top_countries: string[];
  mean_account_age_days: number;
  mean_velocity: number;
}

export interface BankResult {
  id: string;
  name: string;
  tier: string;
  fraud_ratio: number;
  num_transactions: number;
  status: string;
  local_metrics: EvaluationMetrics | null;
  federated_metrics: EvaluationMetrics | null;
  improvement: Record<string, number> | null;
  data_profile: DataProfile | null;
}

export interface TrainingRound {
  round_number: number;
  total_rounds: number;
  global_loss: number;
  participating_banks: string[];
  dropped_banks: string[];
  duration_ms: number;
  privacy_budget: number;
}

export interface SimulationSummary {
  id: string;
  status: string;
  current_round: number;
  total_rounds: number;
  progress_pct: number;
  created_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface SimulationDetail {
  id: string;
  status: string;
  config: SimulationConfig;
  current_round: number;
  total_rounds: number;
  progress_pct: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  error_message: string | null;
  banks: BankResult[];
  rounds: TrainingRound[];
}

export interface SimulationCreateResponse {
  id: string;
  status: string;
  message: string;
}

export interface BankInfo {
  id: string;
  name: string;
  tier: string;
  description: string;
  default_fraud_ratio: number;
  default_transactions: number;
  fraud_pattern: string;
  characteristics: string[];
}

export interface TrainingEvent {
  event_type: string;
  data: Record<string, unknown>;
}

export const BANK_COLORS: Record<string, string> = {
  bank_a: '#6366f1',
  bank_b: '#14b8a6',
  bank_c: '#f59e0b',
};

export const BANK_NAMES: Record<string, string> = {
  bank_a: 'Meridian National',
  bank_b: 'Nexus Digital',
  bank_c: 'Heritage Regional',
};

// ── Phase 2: AML Intelligence Platform ────────

export interface Alert {
  id: string;
  bank_id: string;
  transaction_id: string;
  risk_score: number;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  status: string;
  reason_codes: string[];
  confidence: number;
  involved_entity_ids: string[];
  created_at: string;
  top_features: { feature: string; contribution: number }[];
  risk_factors: string[];
  model_confidence: number;
}

export interface ExplainabilityReport {
  alert_id: string;
  top_features: { feature: string; contribution: number }[];
  risk_factors: string[];
  historical_evidence: string[];
  model_confidence: number;
  risk_score_breakdown: RiskSignalData[];
  explanation_text: string;
}

export interface RiskSignalData {
  signal_name: string;
  weight: number;
  raw_value: number;
  normalized_score: number;
  explanation: string;
}

export interface SharedIntelligence {
  id: string;
  source_bank_id: string;
  intelligence_type: string;
  privacy_hash: string;
  risk_indicator: number;
  description: string;
  entity_type: string | null;
  related_alert_count: number;
  created_at: string;
}

export interface IntelligenceStats {
  total_items: number;
  items_by_type: Record<string, number>;
  items_by_bank: Record<string, number>;
  avg_risk_indicator: number;
}

export interface Case {
  id: string;
  title: string;
  status: string;
  priority: string;
  assigned_to: string | null;
  alert_ids: string[];
  notes: CaseNote[];
  timeline: CaseEvent[];
  created_at: string;
  updated_at: string | null;
  closed_at: string | null;
  total_risk_score: number;
  duration_hours: number | null;
  is_open: boolean;
}

export interface CaseSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  assigned_to: string | null;
  alert_count: number;
  created_at: string;
  is_open: boolean;
}

export interface CaseNote {
  id: string;
  case_id: string;
  author: string;
  content: string;
  created_at: string;
}

export interface CaseEvent {
  event_type: string;
  description: string;
  actor: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface Entity {
  id: string;
  entity_type: string;
  privacy_id: string;
  bank_id: string;
  display_label: string;
  attributes: Record<string, unknown>;
  risk_level: string;
  alert_count: number;
  first_seen: string;
  last_seen: string;
}

export interface EntityProfile {
  entity_id: string;
  entity_type: string;
  privacy_id: string;
  display_label: string;
  bank_id: string;
  risk_level: string;
  alert_count: number;
  relationship_count: number;
  cross_institution_count: number;
  banks_present: string[];
  first_seen: string;
  last_seen: string;
  attributes: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  clusters: string[][];
  center_entity_id: string;
  depth: number;
}

export interface GraphNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: {
    label: string;
    entityType: string;
    bankId: string;
    riskLevel: string;
    alertCount: number;
    isCenter: boolean;
  };
  style: Record<string, string>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
  animated: boolean;
  style: Record<string, string | number>;
  data: { confidence: number; relationshipType: string };
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  nodes_by_risk: Record<string, number>;
  cluster_count: number;
}

export interface ScenarioInfo {
  type: string;
  name: string;
  description: string;
  banks_involved: string[];
  estimated_events: number;
  estimated_duration_seconds: number;
}

export interface ScenarioStartResponse {
  scenario_id: string;
  scenario_type: string;
  name: string;
  total_events: number;
  status: string;
}

export interface ScenarioStatus {
  scenario_id: string;
  status: string;
  total_events: number;
  delivered_events: number;
  speed_multiplier: number;
  started_at: string;
}

export interface StreamingEvent {
  event_id: string;
  event_type: string;
  bank_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
  sequence: number;
  total: number;
  scenario_id: string;
}

export interface DashboardStats {
  total_alerts: number;
  critical_alerts: number;
  open_cases: number;
  total_entities: number;
  shared_intelligence_items: number;
  cross_institution_matches: number;
  active_scenarios: number;
  graph_clusters: number;
}

export interface RiskWeights {
  ml_prediction: number;
  velocity_rules: number;
  merchant_reputation: number;
  country_risk: number;
  device_anomaly: number;
  customer_history: number;
  previous_alerts: number;
  chargeback_history: number;
  behavior_anomaly: number;
}

export const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#3b82f6',
  info: '#6b7280',
};

export const ENTITY_TYPE_COLORS: Record<string, string> = {
  customer: '#6366f1',
  merchant: '#f59e0b',
  device: '#14b8a6',
  card: '#ec4899',
  email: '#8b5cf6',
  phone: '#06b6d4',
  ip_address: '#f43f5e',
};

export const PRIORITY_LABELS: Record<string, string> = {
  p1_critical: 'P1 - Critical',
  p2_high: 'P2 - High',
  p3_medium: 'P3 - Medium',
  p4_low: 'P4 - Low',
};

export const CASE_STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  assigned: 'Assigned',
  investigating: 'Investigating',
  pending_review: 'Pending Review',
  escalated: 'Escalated',
  closed_confirmed: 'Closed (Confirmed)',
  closed_false_positive: 'Closed (FP)',
};
