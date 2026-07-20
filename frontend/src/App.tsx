import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import SimulationView from './pages/SimulationView';
import AlertsPage from './pages/AlertsPage';
import CasesPage from './pages/CasesPage';
import CaseDetailPage from './pages/CaseDetailPage';
import ScenariosPage from './pages/ScenariosPage';
import GraphPage from './pages/GraphPage';
import InvestigationDashboard from './pages/InvestigationDashboard';
import PoliciesPage from './pages/PoliciesPage';
import PsiPage from './pages/PsiPage';
import SecurityPage from './pages/SecurityPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          {/* Phase 1: Federated Learning */}
          <Route path="/" element={<Dashboard />} />
          <Route path="/simulation/:id" element={<SimulationView />} />

          {/* Phase 2: AML Intelligence Platform */}
          <Route path="/investigation" element={<InvestigationDashboard />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/cases" element={<CasesPage />} />
          <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          <Route path="/rules" element={<PoliciesPage />} />
          <Route path="/psi" element={<PsiPage />} />
          <Route path="/security" element={<SecurityPage />} />
          <Route path="/scenarios" element={<ScenariosPage />} />
          <Route path="/graph" element={<GraphPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

