import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  Alert,
  BankInfo,
  Case,
  CaseSummary,
  DashboardStats,
  Entity,
  ExplainabilityReport,
  GraphData,
  GraphStats,
  IntelligenceStats,
  RiskWeights,
  ScenarioInfo,
  ScenarioStartResponse,
  ScenarioStatus,
  SharedIntelligence,
  SimulationConfig,
  SimulationCreateResponse,
  SimulationDetail,
  SimulationSummary,
  TrainingRound,
} from './types';

// ── Phase 1: Simulations ───────────────────

export function useSimulations() {
  return useQuery<SimulationSummary[]>({
    queryKey: ['simulations'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/simulations');
      return data;
    },
    refetchInterval: 3000,
  });
}

export function useSimulation(id: string | undefined) {
  return useQuery<SimulationDetail>({
    queryKey: ['simulation', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/api/v1/simulations/${id}`);
      return data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 2000;
    },
  });
}

export function useCreateSimulation() {
  return useMutation<SimulationCreateResponse, Error, Partial<SimulationConfig>>({
    mutationFn: async (config) => {
      const { data } = await apiClient.post('/api/v1/simulations', config);
      return data;
    },
  });
}

export function useBanks() {
  return useQuery<BankInfo[]>({
    queryKey: ['banks'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/banks');
      return data;
    },
  });
}

export function useTrainingRounds(simulationId: string | undefined) {
  return useQuery<TrainingRound[]>({
    queryKey: ['training-rounds', simulationId],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/api/v1/training/${simulationId}/rounds`,
      );
      return data;
    },
    enabled: !!simulationId,
    refetchInterval: 3000,
  });
}

// ── Phase 2: Alerts ────────────────────────

export function useAlerts(filters?: { bank_id?: string; severity?: string; status?: string }) {
  return useQuery<Alert[]>({
    queryKey: ['alerts', filters],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/alerts', { params: filters });
      return data;
    },
    refetchInterval: 5000,
  });
}

export function useAlert(id: string | undefined) {
  return useQuery<Alert>({
    queryKey: ['alert', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/api/v1/alerts/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useAlertExplainability(alertId: string | undefined) {
  return useQuery<ExplainabilityReport>({
    queryKey: ['alert-explain', alertId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/api/v1/alerts/${alertId}/explain`);
      return data;
    },
    enabled: !!alertId,
  });
}

export function useIntelligence(bankId?: string) {
  return useQuery<SharedIntelligence[]>({
    queryKey: ['intelligence', bankId],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/intelligence', {
        params: bankId ? { bank_id: bankId } : {},
      });
      return data;
    },
    refetchInterval: 5000,
  });
}

export function useIntelligenceStats() {
  return useQuery<IntelligenceStats>({
    queryKey: ['intelligence-stats'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/intelligence/stats');
      return data;
    },
    refetchInterval: 10000,
  });
}

// ── Phase 2: Cases ─────────────────────────

export function useCases(filters?: { status?: string; priority?: string }) {
  return useQuery<CaseSummary[]>({
    queryKey: ['cases', filters],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/cases', { params: filters });
      return data;
    },
    refetchInterval: 5000,
  });
}

export function useCase(id: string | undefined) {
  return useQuery<Case>({
    queryKey: ['case', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/api/v1/cases/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateCase() {
  return useMutation<Case, Error, { title: string; priority?: string; alert_ids?: string[] }>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post('/api/v1/cases', payload);
      return data;
    },
  });
}

export function useUpdateCaseStatus() {
  return useMutation<Case, Error, { caseId: string; status: string; actor?: string }>({
    mutationFn: async ({ caseId, ...body }) => {
      const { data } = await apiClient.patch(`/api/v1/cases/${caseId}`, body);
      return data;
    },
  });
}

export function useAddCaseNote() {
  return useMutation<unknown, Error, { caseId: string; author: string; content: string }>({
    mutationFn: async ({ caseId, ...body }) => {
      const { data } = await apiClient.post(`/api/v1/cases/${caseId}/notes`, body);
      return data;
    },
  });
}

// ── Phase 2: Entities ──────────────────────

export function useEntities(filters?: { entity_type?: string; bank_id?: string; risk_level?: string }) {
  return useQuery<Entity[]>({
    queryKey: ['entities', filters],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/entities', { params: filters });
      return data;
    },
    refetchInterval: 10000,
  });
}

// ── Phase 2: Graph ─────────────────────────

export function useGraph(entityId: string | undefined, depth: number = 2) {
  return useQuery<GraphData>({
    queryKey: ['graph', entityId, depth],
    queryFn: async () => {
      const { data } = await apiClient.get(`/api/v1/graph/${entityId}`, {
        params: { depth },
      });
      return data;
    },
    enabled: !!entityId,
  });
}

export function useGraphStats() {
  return useQuery<GraphStats>({
    queryKey: ['graph-stats'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/graph/stats/summary');
      return data;
    },
    refetchInterval: 10000,
  });
}

// ── Phase 2: Scenarios ─────────────────────

export function useScenarios() {
  return useQuery<ScenarioInfo[]>({
    queryKey: ['scenarios'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/scenarios');
      return data;
    },
  });
}

export function useStartScenario() {
  return useMutation<ScenarioStartResponse, Error, { scenario_type: string; speed_multiplier?: number }>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post('/api/v1/scenarios/start', payload);
      return data;
    },
  });
}

export function useScenarioStatus(scenarioId: string | undefined) {
  return useQuery<ScenarioStatus>({
    queryKey: ['scenario-status', scenarioId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/api/v1/scenarios/${scenarioId}/status`);
      return data;
    },
    enabled: !!scenarioId,
    refetchInterval: 1000,
  });
}

// ── Phase 2: Dashboard ─────────────────────

export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/dashboard/stats');
      return data;
    },
    refetchInterval: 5000,
  });
}

export function useRiskWeights() {
  return useQuery<RiskWeights>({
    queryKey: ['risk-weights'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/dashboard/risk-weights');
      return data;
    },
  });
}

export function useAlertsBySeverity() {
  return useQuery<Record<string, number>>({
    queryKey: ['alerts-by-severity'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/dashboard/alerts-by-severity');
      return data;
    },
    refetchInterval: 10000,
  });
}

export function useAlertsByBank() {
  return useQuery<Record<string, number>>({
    queryKey: ['alerts-by-bank'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/dashboard/alerts-by-bank');
      return data;
    },
    refetchInterval: 10000,
  });
}
