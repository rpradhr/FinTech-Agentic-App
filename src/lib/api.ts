import axios, { AxiosError } from "axios";
import {
  mockState,
  mockApproveFraud,
  mockIngestTransaction,
  mockDecideLoan,
  mockApproveAdvice,
  mockBranchAnalysis,
  mockChat,
  mockHealth,
} from "./mockData";

/**
 * FastAPI client for FinTech Agentic Banking Platform.
 *
 * Demo Mode: when no VITE_API_BASE_URL is configured, OR when the user toggles
 * "demo" via the in-app switch, all calls are served from in-memory mock data
 * so the UI works end-to-end without a running backend.
 */
const ENV_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
const DEMO_KEY = "fintech_demo_mode";

export const demoMode = {
  // Default to demo when no real backend URL was configured at build time.
  isOn: (): boolean => {
    if (typeof localStorage === "undefined") return !ENV_BASE;
    const v = localStorage.getItem(DEMO_KEY);
    if (v === "on") return true;
    if (v === "off") return false;
    return !ENV_BASE;
  },
  set: (on: boolean) => {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(DEMO_KEY, on ? "on" : "off");
    }
  },
};

export const apiBaseUrl = ENV_BASE || "/api";

export const api = axios.create({
  baseURL: apiBaseUrl,
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

// Simulate network latency for a more realistic feel.
const delay = <T,>(value: T, ms = 280): Promise<T> =>
  new Promise((res) => setTimeout(() => res(value), ms));

// ── Types ────────────────────────────────────────────────────────────────────
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

// ── Endpoints (demo-aware) ───────────────────────────────────────────────────
export const endpoints = {
  health: () =>
    demoMode.isOn() ? delay(mockHealth(), 120) : wrap<{ status: string; env: string }>(api.get("/health")),

  // Auth
  devLogin: (user_id: string, roles: string[]) => {
    if (demoMode.isOn()) {
      const token = `demo-${user_id}-${Date.now()}`;
      auth.setToken(token);
      auth.setUser({ user_id, roles });
      return delay({ access_token: token, token_type: "bearer" });
    }
    return wrap<{ access_token: string; token_type: string }>(
      api.post("/auth/dev-token", { user_id, roles }),
    ).then((r) => {
      auth.setToken(r.access_token);
      auth.setUser({ user_id, roles });
      return r;
    });
  },

  // Fraud
  listFraudAlerts: () =>
    demoMode.isOn()
      ? delay([...mockState.fraudAlerts])
      : wrap<FraudAlert[]>(api.get("/fraud/alerts")),
  getFraudAlert: (id: string) =>
    demoMode.isOn()
      ? delay(mockState.fraudAlerts.find((a) => a.alert_id === id)!)
      : wrap<FraudAlert>(api.get(`/fraud/alerts/${id}`)),
  approveFraud: (id: string, body: { analyst_id: string; decision: FraudDecision; notes?: string }) =>
    demoMode.isOn()
      ? delay(mockApproveFraud(id, body.decision))
      : wrap<FraudAlert>(api.post(`/fraud/alerts/${id}/approve`, body)),
  ingestTransaction: (payload: Record<string, unknown>) =>
    demoMode.isOn()
      ? delay(mockIngestTransaction())
      : wrap<FraudAlert>(api.post("/fraud/events", payload)),

  // Loans
  getLoanReview: (applicationId: string) =>
    demoMode.isOn()
      ? mockState.loans[applicationId]
        ? delay(mockState.loans[applicationId])
        : Promise.reject(new ApiError(404, `Application ${applicationId} not found (try loan-001, loan-002, loan-003)`))
      : wrap<LoanReview>(api.get(`/loans/applications/${applicationId}/review`)),
  decideLoan: (
    applicationId: string,
    body: { underwriter_id: string; decision: string; notes?: string },
  ) =>
    demoMode.isOn()
      ? delay(mockDecideLoan(applicationId, body.decision))
      : wrap<LoanReview>(api.post(`/loans/applications/${applicationId}/decision`, body)),

  // Interactions / Sentiment
  getCustomerSignal: (customerId: string) =>
    demoMode.isOn()
      ? mockState.sentiment[customerId]
        ? delay(mockState.sentiment[customerId])
        : Promise.reject(
            new ApiError(404, `Customer ${customerId} has no sentiment signal (try cust-001, cust-007, cust-014)`),
          )
      : wrap<Record<string, unknown>>(api.get(`/interactions/customers/${customerId}/signals`)),

  // Advisory
  getAdviceDraft: (customerId: string, advisor_id?: string) =>
    demoMode.isOn()
      ? mockState.advice[customerId]
        ? delay(mockState.advice[customerId])
        : Promise.reject(
            new ApiError(404, `No draft for ${customerId} (try cust-001, cust-014)`),
          )
      : wrap<AdviceDraft>(
          api.get(`/advisory/customers/${customerId}/recommendations`, {
            params: advisor_id ? { advisor_id } : {},
          }),
        ),
  approveAdvice: (
    draftId: string,
    body: { advisor_id: string; advisor_edits?: string | null },
  ) =>
    demoMode.isOn()
      ? delay(mockApproveAdvice(draftId))
      : wrap<AdviceDraft>(api.post(`/advisory/recommendations/${draftId}/approve`, body)),

  // Branches
  branchDashboard: () =>
    demoMode.isOn()
      ? delay([...mockState.branches])
      : wrap<BranchSummary[]>(api.get("/branches/dashboard")),
  branchInsights: (id: string) =>
    demoMode.isOn()
      ? mockState.branchInsights[id]
        ? delay(mockState.branchInsights[id])
        : Promise.reject(new ApiError(404, `Branch ${id} not found`))
      : wrap<Record<string, unknown>>(api.get(`/branches/${id}/insights`)),
  analyzeBranch: (id: string) =>
    demoMode.isOn()
      ? delay(mockBranchAnalysis(id), 600)
      : wrap<Record<string, unknown>>(api.post(`/branches/${id}/analyze`)),

  // Cases
  listCases: (case_type?: string) =>
    demoMode.isOn()
      ? delay(case_type ? mockState.cases.filter((c) => c.case_type === case_type) : [...mockState.cases])
      : wrap<Record<string, unknown>[]>(api.get("/cases", { params: case_type ? { case_type } : {} })),

  // Chat
  chatQuery: (message: string, _history: { role: string; content: string }[] = []) =>
    demoMode.isOn()
      ? delay(mockChat(message), 500)
      : wrap<ChatQueryResponse>(api.post("/chat/query", { message, history: _history })),
};
