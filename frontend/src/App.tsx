import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import AuditResultsPage from './pages/AuditResultsPage';
import NegotiationPage from './pages/NegotiationPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import PricingPage from './pages/PricingPage';
import NotFoundPage from './pages/NotFoundPage';
import ProtectedRoute from './components/auth/ProtectedRoute';

// B2B Pages (Hospital Portal)
import B2BLoginPage from './pages/b2b/B2BLoginPage';
import B2BRegisterPage from './pages/b2b/B2BRegisterPage';
import B2BDashboardPage from './pages/b2b/B2BDashboardPage';

function App() {
  return (
    <Routes>
      {/* ============================================ */}
      {/* B2C Routes (Patients/Users) */}
      {/* ============================================ */}
      
      {/* Public routes */}
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected routes with layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/audit/:documentId" element={<AuditResultsPage />} />
        <Route path="/negotiate" element={<NegotiationPage />} />
        <Route path="/negotiate/:documentId" element={<NegotiationPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      {/* ============================================ */}
      {/* B2B Routes (Hospital Portal) */}
      {/* ============================================ */}
      
      {/* B2B Public routes */}
      <Route path="/b2b/login" element={<B2BLoginPage />} />
      <Route path="/b2b/register" element={<B2BRegisterPage />} />
      
      {/* B2B Protected routes (auth handled in component) */}
      <Route path="/b2b/dashboard" element={<B2BDashboardPage />} />
      <Route path="/b2b" element={<B2BLoginPage />} />

      {/* 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default App;
