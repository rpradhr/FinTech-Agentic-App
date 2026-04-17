import axios, { AxiosError } from "axios";

/**
 * FastAPI client for FinTech Agentic Banking Platform.
 * Configure backend URL via VITE_API_BASE_URL (defaults to /api proxy).
 */
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

const TOKEN_KEY = "fintech_access_token";
const USER_KEY = "fintech_user";

export const auth = {
  getToken: () => (typeof localStorage !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null),
  setToken: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clearToken: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  getUser: (): { user_id: string; roles: string[] } | null => {
    if (typeof localStorage === "undefined") return null;
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },
  setUser: (u: { user_id: string; roles: string[] }) =>
    localStorage.setItem(USER_KEY, JSON.stringify(u)),
};

api.interceptors.request.use((config) => {
  const token = auth.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export class ApiError extends Error {
  constructor(public status: number, message: string, public data?: unknown) {
    super(message);
  }
}

const wrap = <T,>(p: Promise<{ data: T }>): Promise<T> =>
  p.then((r) => r.data).catch((e: AxiosError<{ detail?: string }>) => {
    const status = e.response?.status ?? 0;
    const detail = e.response?.data?.detail ?? e.message ?? "Request failed";
    throw new ApiError(status, detail, e.response?.data);
  });

// ── Types (match backend schemas) ────────────────────────────────────────────
export type FraudDecision = "approved" | "declined" | "escalated";

export interface FraudAlert {
  alert_id: string;
  transaction_id: string;
  customer_id: string;
  risk_score: number;
  status: string;
  reason?: string;
  created_at?: string;
  amount?: number;
  merchant?: string;
  [k: string]: unknown;
}

export interface LoanReview {
  application_id: string;
  customer_id?: string;
  recommendation?: string;
  dti?: number;
  ltv?: number;
  rationale?: string;
  status?: string;
  [k: string]: unknown;
}

export interface AdviceDraft {
  draft_id: string;
  customer_id: string;
  recommendations: string[] | string;
  status?: string;
  [k: string]: unknown;
}

export interface BranchSummary {
  branch_id: string;
  name?: string;
  region?: string;
  health_score?: number;
  wait_time_avg?: number;
  open_issues?: number;
  [k: string]: unknown;
}

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

// ── Endpoints ────────────────────────────────────────────────────────────────
export const endpoints = {
  health: () => wrap<{ status: string; env: string }>(api.get("/health")),

  // Auth
  devLogin: (user_id: string, roles: string[]) =>
    wrap<{ access_token: string; token_type: string }>(
      api.post("/auth/dev-token", { user_id, roles }),
    ).then((r) => {
      auth.setToken(r.access_token);
      auth.setUser({ user_id, roles });
      return r;
    }),

  // Fraud
  listFraudAlerts: () => wrap<FraudAlert[]>(api.get("/fraud/alerts")),
  getFraudAlert: (id: string) => wrap<FraudAlert>(api.get(`/fraud/alerts/${id}`)),
  approveFraud: (id: string, body: { analyst_id: string; decision: FraudDecision; notes?: string }) =>
    wrap<FraudAlert>(api.post(`/fraud/alerts/${id}/approve`, body)),
  ingestTransaction: (payload: Record<string, unknown>) =>
    wrap<FraudAlert>(api.post("/fraud/events", payload)),

  // Loans
  getLoanReview: (applicationId: string) =>
    wrap<LoanReview>(api.get(`/loans/applications/${applicationId}/review`)),
  decideLoan: (
    applicationId: string,
    body: { underwriter_id: string; decision: string; notes?: string },
  ) => wrap<LoanReview>(api.post(`/loans/applications/${applicationId}/decision`, body)),

  // Interactions / Sentiment
  getCustomerSignal: (customerId: string) =>
    wrap<Record<string, unknown>>(api.get(`/interactions/customers/${customerId}/signals`)),

  // Advisory
  getAdviceDraft: (customerId: string, advisor_id?: string) =>
    wrap<AdviceDraft>(
      api.get(`/advisory/customers/${customerId}/recommendations`, {
        params: advisor_id ? { advisor_id } : {},
      }),
    ),
  approveAdvice: (
    draftId: string,
    body: { advisor_id: string; advisor_edits?: string | null },
  ) => wrap<AdviceDraft>(api.post(`/advisory/recommendations/${draftId}/approve`, body)),

  // Branches
  branchDashboard: () => wrap<BranchSummary[]>(api.get("/branches/dashboard")),
  branchInsights: (id: string) =>
    wrap<Record<string, unknown>>(api.get(`/branches/${id}/insights`)),
  analyzeBranch: (id: string) =>
    wrap<Record<string, unknown>>(api.post(`/branches/${id}/analyze`)),

  // Cases
  listCases: (case_type?: string) =>
    wrap<Record<string, unknown>[]>(api.get("/cases", { params: case_type ? { case_type } : {} })),

  // Chat
  chatQuery: (message: string, history: { role: string; content: string }[] = []) =>
    wrap<ChatQueryResponse>(api.post("/chat/query", { message, history })),
};

export const apiBaseUrl = BASE_URL;
