import { Routes, Route } from 'react-router-dom';
import ConsoleShell from './components/layout/ConsoleShell';
import { AstraeaProvider } from './context/AstraeaContext';
import Dashboard from './pages/Dashboard';
import Distribution from './pages/Distribution';
import RecipientTerminal from './pages/RecipientTerminal';
import SecureViewer from './pages/SecureViewer';
import InvestigatorPortal from './pages/InvestigatorPortal';
import AttributionResult from './pages/AttributionResult';
import SystemStatus from './pages/SystemStatus';

export default function App() {
  return (
    <AstraeaProvider>
      <ConsoleShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/distribution" element={<Distribution />} />
          <Route path="/recipient" element={<RecipientTerminal />} />
          <Route path="/viewer" element={<SecureViewer />} />
          <Route path="/investigator" element={<InvestigatorPortal />} />
          <Route path="/attribution" element={<AttributionResult />} />
          <Route path="/system" element={<SystemStatus />} />
        </Routes>
      </ConsoleShell>
    </AstraeaProvider>
  );
}
