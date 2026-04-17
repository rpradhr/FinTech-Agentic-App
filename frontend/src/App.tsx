import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import OperationsHome from "@/pages/OperationsHome";
import { FraudAlertList, FraudAlertDetail } from "@/pages/FraudWorkbench";
import { LoanReviewList } from "@/pages/LoanWorkbench";
import AdvisorWorkspace from "@/pages/AdvisorWorkspace";
import BranchMonitor from "@/pages/BranchMonitor";
import AuditConsole from "@/pages/AuditConsole";
import AdminDashboard from "@/pages/AdminDashboard";
import ChatPage from "@/pages/ChatPage";
import { useAuthStore } from "@/store/auth";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<OperationsHome />} />
        <Route path="dashboard" element={<AdminDashboard />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="fraud" element={<FraudAlertList />} />
        <Route path="fraud/:alertId" element={<FraudAlertDetail />} />
        <Route path="loans" element={<LoanReviewList />} />
        <Route path="advisory" element={<AdvisorWorkspace />} />
        <Route path="branches" element={<BranchMonitor />} />
        <Route path="audit" element={<AuditConsole />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
