// ─── Domain types mirroring the backend API responses ───────────────────────

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type FraudStatus =
  | "pending_analyst_review"
  | "under_investigation"
  | "confirmed_fraud"
  | "cleared"
  | "escalated";

export interface FraudAlert {
  alert_id: string;
  txn_id: string;
  customer_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  reasons: string[];
  recommended_action: string;
  ai_explanation: string | null;
  status: FraudStatus;
  created_at: string;
}

export interface LoanReview {
  review_id: string;
  application_id: string;
  customer_id: string;
  summary: string;
  missing_documents: string[];
  recommended_status: string;
  confidence_score: number;
  ai_explanation: string | null;
  underwriter_decision: string | null;
  created_at: string;
}

export interface CustomerSignal {
  customer_id: string;
  overall_sentiment: string;
  recent_drivers: string[];
  churn_risk: number;
  suppress_cross_sell: boolean;
  updated_at: string;
}

export interface AdviceDraft {
  draft_id: string;
  customer_id: string;
  advisor_id: string | null;
  next_best_actions: NextBestAction[];
  customer_context_summary: string;
  goals_summary: string;
  product_gaps?: string[];
  service_sentiment_note: string | null;
  suppress_cross_sell: boolean;
  full_advice_text: string;
  status: string;
  created_at: string;
}

export interface NextBestAction {
  action_id: string;
  category: string;
  title: string;
  rationale: string;
  evidence: string[];
  suggested_script: string | null;
  priority: number;
  suitability_flags: string[];
}

export interface BranchInsight {
  insight_id: string;
  branch_id: string;
  issue_summary: string;
  probable_causes: string[];
  ranked_recommendations: string[];
  created_at: string;
}

export interface BranchDashboardEntry {
  branch_id: string;
  branch_name: string | null;
  report_date: string;
  avg_wait_time_minutes: number | null;
  complaint_count: number;
  new_accounts_opened: number;
}

export interface Case {
  case_id: string;
  case_type: string;
  status: string;
  priority: string;
  title: string;
  customer_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  event_id: string;
  actor_type: string;
  actor_id: string;
  action: string;
  related_object_id: string;
  related_object_type: string;
  customer_id: string | null;
  notes: string | null;
  ts: string;
}
