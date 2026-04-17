import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Attach auth token from localStorage on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Auth ─────────────────────────────────────────────────────────────────────

export const devLogin = async (userId: string, roles: string[]) => {
  const res = await api.post("/auth/dev-token", { user_id: userId, roles });
  localStorage.setItem("access_token", res.data.access_token);
  return res.data;
};

// ── Fraud ─────────────────────────────────────────────────────────────────────

export const fetchFraudAlerts = () => api.get("/fraud/alerts").then((r) => r.data);

export const getFraudAlert = (alertId: string) =>
  api.get(`/fraud/alerts/${alertId}`).then((r) => r.data);

export const approveFraudAlert = (
  alertId: string,
  analystId: string,
  decision: "approved" | "declined" | "escalated",
  notes?: string
) =>
  api
    .post(`/fraud/alerts/${alertId}/approve`, {
      analyst_id: analystId,
      decision,
      notes,
    })
    .then((r) => r.data);

export const ingestTransaction = (payload: Record<string, unknown>) =>
  api.post("/fraud/events", payload).then((r) => r.data);

// ── Loans ─────────────────────────────────────────────────────────────────────

export const getLoanReview = (applicationId: string) =>
  api.get(`/loans/applications/${applicationId}/review`).then((r) => r.data);

export const submitLoanDecision = (
  applicationId: string,
  underwriterId: string,
  decision: string,
  notes?: string
) =>
  api
    .post(`/loans/applications/${applicationId}/decision`, {
      underwriter_id: underwriterId,
      decision,
      notes,
    })
    .then((r) => r.data);

// ── Interactions ──────────────────────────────────────────────────────────────

export const getCustomerSignal = (customerId: string) =>
  api.get(`/interactions/customers/${customerId}/signals`).then((r) => r.data);

// ── Advisory ──────────────────────────────────────────────────────────────────

export const getAdviceDraft = (customerId: string, advisorId?: string) => {
  const params = advisorId ? { advisor_id: advisorId } : {};
  return api
    .get(`/advisory/customers/${customerId}/recommendations`, { params })
    .then((r) => r.data);
};

export const approveAdviceDraft = (
  draftId: string,
  advisorId: string,
  advisorEdits?: string
) =>
  api
    .post(`/advisory/recommendations/${draftId}/approve`, {
      advisor_id: advisorId,
      advisor_edits: advisorEdits || null,
    })
    .then((r) => r.data);

// ── Branches ──────────────────────────────────────────────────────────────────

export const getBranchDashboard = () =>
  api.get("/branches/dashboard").then((r) => r.data);

export const getBranchInsights = (branchId: string) =>
  api.get(`/branches/${branchId}/insights`).then((r) => r.data);

export const triggerBranchAnalysis = (branchId: string) =>
  api.post(`/branches/${branchId}/analyze`).then((r) => r.data);

// ── Cases & Audit ─────────────────────────────────────────────────────────────

export const getOpenCases = (caseType?: string) => {
  const params = caseType ? { case_type: caseType } : {};
  return api.get("/cases", { params }).then((r) => r.data);
};

export const getAuditTrail = (objectId: string) =>
  api.get(`/audit/${objectId}`).then((r) => r.data);

export const getAgentMetrics = () =>
  api.get("/metrics/agents").then((r) => r.data);

// ── Chat / NL interface ───────────────────────────────────────────────────────

export interface ChatCard {
  type: "alert" | "metric" | "action" | "summary" | "evidence";
  title: string;
  value?: string;
  subtitle?: string;
  status?: string;
  items?: string[];
  color?: string;
}

export interface ChatQueryResponse {
  agent_type: string;
  content: string;
  cards: ChatCard[];
}

export const sendChatQuery = (
  message: string,
  history: { role: string; content: string }[] = []
): Promise<ChatQueryResponse> =>
  api
    .post("/chat/query", { message, history })
    .then((r) => r.data);

export default api;
