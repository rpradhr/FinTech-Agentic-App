/**
 * In-memory mock dataset for Demo Mode.
 * Mirrors the FastAPI backend's response shapes so the UI is identical.
 */
import type {
  FraudAlert,
  LoanReview,
  AdviceDraft,
  BranchSummary,
  ChatQueryResponse,
} from "./api";

const now = () => new Date().toISOString();
const minutesAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString();

export const mockState = {
  fraudAlerts: [
    {
      alert_id: "alr-9821",
      transaction_id: "tx-44021",
      customer_id: "cust-001",
      risk_score: 0.92,
      status: "pending_review",
      reason:
        "Card-present transaction in Lagos, Nigeria 18 minutes after a card-not-present charge in Austin, TX. Geo-velocity impossible.",
      amount: 2480,
      merchant: "GoldStar Electronics",
      created_at: minutesAgo(8),
    },
    {
      alert_id: "alr-9822",
      transaction_id: "tx-44033",
      customer_id: "cust-014",
      risk_score: 0.74,
      status: "pending_review",
      reason:
        "Five micro-charges ($1.02–$1.18) within 90 seconds at merchants previously linked to card-testing rings.",
      amount: 5.6,
      merchant: "QuickPay Gateway",
      created_at: minutesAgo(22),
    },
    {
      alert_id: "alr-9823",
      transaction_id: "tx-44052",
      customer_id: "cust-007",
      risk_score: 0.58,
      status: "pending_review",
      reason: "Amount 6.2× customer's 90-day average; new device fingerprint.",
      amount: 1899,
      merchant: "Nimbus Travel Co.",
      created_at: minutesAgo(41),
    },
    {
      alert_id: "alr-9824",
      transaction_id: "tx-44060",
      customer_id: "cust-022",
      risk_score: 0.31,
      status: "pending_review",
      reason: "Out-of-pattern weekend ATM withdrawal; customer rarely uses ATMs.",
      amount: 400,
      merchant: "Atlas Credit Union ATM",
      created_at: minutesAgo(67),
    },
    {
      alert_id: "alr-9825",
      transaction_id: "tx-44071",
      customer_id: "cust-031",
      risk_score: 0.87,
      status: "pending_review",
      reason: "Recurring subscription suddenly increased 12×; merchant flagged in fraud feed.",
      amount: 359.99,
      merchant: "StreamPlus Premium",
      created_at: minutesAgo(95),
    },
  ] as FraudAlert[],

  loans: {
    "loan-001": {
      application_id: "loan-001",
      customer_id: "cust-001",
      recommendation: "approve_with_conditions",
      dti: 0.34,
      ltv: 0.78,
      status: "ready_for_underwriter",
      rationale:
        "Applicant shows stable 5-year employment at a Fortune 500 employer with 18% YoY income growth. DTI of 34% is within policy. LTV of 78% requires PMI but is acceptable. Recommend approval contingent on (1) updated 30-day pay stubs and (2) confirmation of source of $14,200 deposit on 03/12.",
    },
    "loan-002": {
      application_id: "loan-002",
      customer_id: "cust-014",
      recommendation: "decline",
      dti: 0.58,
      ltv: 0.94,
      status: "ready_for_underwriter",
      rationale:
        "DTI of 58% exceeds policy ceiling of 45%. LTV of 94% combined with two 30-day late payments in the past 12 months indicates elevated default risk. Recommend decline; suggest applicant pay down revolving balances and reapply in 6 months.",
    },
    "loan-003": {
      application_id: "loan-003",
      customer_id: "cust-007",
      recommendation: "request_changes",
      dti: 0.41,
      ltv: 0.82,
      status: "awaiting_documents",
      rationale:
        "Application is missing the most recent two months of bank statements and a signed gift-funds letter for the $25,000 down-payment contribution. Cannot finalize underwriting until documents are received.",
    },
  } as Record<string, LoanReview>,

  advice: {
    "cust-001": {
      draft_id: "draft-5501",
      customer_id: "cust-001",
      status: "pending_advisor_review",
      recommendations: [
        "Move $18,400 from checking to the high-yield savings product (4.35% APY) to capture an estimated $760/yr in additional interest.",
        "Consolidate two credit cards (combined $9,120 balance at 21.9% APR) into the personal-loan product at 11.4% APR to save ~$960/yr in interest.",
        "Increase 401(k) contribution from 6% to 8% to fully capture employer match — annualized benefit ~$2,400.",
        "Schedule a beneficiary review: current beneficiaries on the IRA were last updated in 2018, before marriage.",
      ],
    },
    "cust-014": {
      draft_id: "draft-5502",
      customer_id: "cust-014",
      status: "pending_advisor_review",
      recommendations: [
        "Pause cross-sell: customer recorded two negative service interactions in the last 30 days.",
        "Offer fee-waiver gesture on the $35 overdraft charge (03/29) to recover NPS.",
        "Schedule advisor courtesy call within 7 days; do NOT lead with new products.",
      ],
    },
  } as Record<string, AdviceDraft>,

  branches: [
    {
      branch_id: "br-001",
      name: "Downtown Flagship",
      region: "West",
      health_score: 0.86,
      wait_time_avg: 4.2,
      open_issues: 1,
    },
    {
      branch_id: "br-002",
      name: "Northgate",
      region: "West",
      health_score: 0.71,
      wait_time_avg: 7.5,
      open_issues: 3,
    },
    {
      branch_id: "br-003",
      name: "Riverside Plaza",
      region: "Central",
      health_score: 0.42,
      wait_time_avg: 14.8,
      open_issues: 7,
    },
    {
      branch_id: "br-004",
      name: "Eastpark Square",
      region: "East",
      health_score: 0.63,
      wait_time_avg: 9.1,
      open_issues: 4,
    },
    {
      branch_id: "br-005",
      name: "Harbor Point",
      region: "East",
      health_score: 0.79,
      wait_time_avg: 5.6,
      open_issues: 2,
    },
  ] as BranchSummary[],

  branchInsights: {
    "br-001": {
      summary:
        "Top-performing branch. Wait times trending down 12% MoM; new-account opens +18% QoQ. One open complaint pending resolution.",
      kpis: {
        nps: 71,
        new_accounts_30d: 142,
        complaint_count_30d: 3,
        staffing_ratio: 1.0,
      },
      recommendations: [
        "Use as benchmark for Riverside Plaza staffing model.",
        "Resolve open complaint #C-7741 within SLA (48h remaining).",
      ],
    },
    "br-002": {
      summary:
        "Healthy but wait times creeping above target on Saturday mornings. Two tellers on extended leave.",
      kpis: { nps: 58, new_accounts_30d: 89, complaint_count_30d: 6, staffing_ratio: 0.78 },
      recommendations: [
        "Add one floating teller for Saturday 9–1 shift.",
        "Cross-train two CSRs on basic teller transactions.",
      ],
    },
    "br-003": {
      summary:
        "Branch is in operational distress. Wait times nearly 3× regional target; complaint volume up 4× YoY; NPS at 28.",
      kpis: { nps: 28, new_accounts_30d: 31, complaint_count_30d: 24, staffing_ratio: 0.55 },
      recommendations: [
        "URGENT: Escalate to regional VP for staffing relief.",
        "Open temporary digital-only kiosks to absorb queue.",
        "Conduct manager 1:1; consider interim leadership coverage.",
      ],
    },
    "br-004": {
      summary: "Mid-tier performance. Complaint mix concentrated on mortgage origination delays.",
      kpis: { nps: 51, new_accounts_30d: 67, complaint_count_30d: 11, staffing_ratio: 0.84 },
      recommendations: [
        "Co-locate a mortgage specialist 2 days/week.",
        "Audit document-collection flow for redundant steps.",
      ],
    },
    "br-005": {
      summary: "Stable. Strong wealth-management cross-sell; light foot traffic in afternoons.",
      kpis: { nps: 66, new_accounts_30d: 104, complaint_count_30d: 4, staffing_ratio: 1.0 },
      recommendations: [
        "Pilot afternoon advisor walk-in slots.",
        "Promote weekend financial-planning seminars.",
      ],
    },
  } as Record<string, Record<string, unknown>>,

  sentiment: {
    "cust-001": {
      customer_id: "cust-001",
      sentiment: "positive",
      score: 0.62,
      summary:
        "Customer expressed satisfaction with the recent mortgage refinance experience and proactively referred a colleague.",
      recent: [
        {
          channel: "phone",
          ts: minutesAgo(2880),
          excerpt: "Thanks again — the refi closed faster than I expected.",
          score: 0.78,
        },
        {
          channel: "chat",
          ts: minutesAgo(7200),
          excerpt: "Could you also help my coworker open an account?",
          score: 0.55,
        },
      ],
    },
    "cust-014": {
      customer_id: "cust-014",
      sentiment: "negative",
      score: -0.71,
      summary:
        "Two consecutive negative interactions about an overdraft fee and a long branch wait. Cross-sell suppression recommended.",
      recent: [
        {
          channel: "branch",
          ts: minutesAgo(1440),
          excerpt: "Waited 25 minutes just to deposit a check. Considering moving banks.",
          score: -0.82,
        },
        {
          channel: "phone",
          ts: minutesAgo(2160),
          excerpt: "I want this overdraft fee reversed — it's the third one this year.",
          score: -0.6,
        },
      ],
    },
    "cust-007": {
      customer_id: "cust-007",
      sentiment: "neutral",
      score: 0.05,
      summary: "Routine interactions; no strong positive or negative signals in the last 90 days.",
      recent: [
        {
          channel: "chat",
          ts: minutesAgo(4320),
          excerpt: "Can you confirm my statement was mailed?",
          score: 0.0,
        },
      ],
    },
  } as Record<string, Record<string, unknown>>,

  cases: [
    {
      case_id: "case-2210",
      case_type: "fraud",
      status: "open",
      subject: "alr-9821 — Geo-velocity anomaly",
      assigned_to: "analyst-1",
      created_at: minutesAgo(8),
    },
    {
      case_id: "case-2211",
      case_type: "loan",
      status: "open",
      subject: "loan-002 — DTI ceiling breach",
      assigned_to: "uw-1",
      created_at: minutesAgo(180),
    },
    {
      case_id: "case-2212",
      case_type: "advisory",
      status: "open",
      subject: "draft-5501 — NBA package for cust-001",
      assigned_to: "adv-1",
      created_at: minutesAgo(45),
    },
    {
      case_id: "case-2213",
      case_type: "branch",
      status: "open",
      subject: "br-003 — Operational escalation",
      assigned_to: "bm-1",
      created_at: minutesAgo(360),
    },
  ],
};

// ── Mutations on mock state ─────────────────────────────────────────────────
export function mockApproveFraud(
  id: string,
  decision: "approved" | "declined" | "escalated",
): FraudAlert {
  const a = mockState.fraudAlerts.find((x) => x.alert_id === id);
  if (!a) throw new Error(`Alert ${id} not found`);
  a.status = decision;
  return a;
}

export function mockIngestTransaction(): FraudAlert {
  const newAlert: FraudAlert = {
    alert_id: `alr-${9826 + mockState.fraudAlerts.length}`,
    transaction_id: `tx-${Math.floor(Math.random() * 90000 + 10000)}`,
    customer_id: `cust-${String(Math.floor(Math.random() * 40) + 1).padStart(3, "0")}`,
    risk_score: Math.round(Math.random() * 100) / 100,
    status: "pending_review",
    reason: "Newly ingested demo transaction for evaluation.",
    amount: Math.round(Math.random() * 4000 + 50),
    merchant: ["BlueWave Cafe", "Pixel Hardware", "Aurora Markets", "Unknown Merchant"][
      Math.floor(Math.random() * 4)
    ],
    created_at: now(),
  };
  mockState.fraudAlerts.unshift(newAlert);
  return newAlert;
}

export function mockDecideLoan(id: string, decision: string): LoanReview {
  const l = mockState.loans[id];
  if (!l) throw new Error(`Application ${id} not found`);
  l.status = decision;
  return l;
}

export function mockApproveAdvice(draftId: string): AdviceDraft {
  const d = Object.values(mockState.advice).find((x) => x.draft_id === draftId);
  if (!d) throw new Error(`Draft ${draftId} not found`);
  d.status = "approved_for_delivery";
  return d;
}

export function mockBranchAnalysis(id: string): Record<string, unknown> {
  const insights = mockState.branchInsights[id];
  if (!insights) throw new Error(`Branch ${id} not found`);
  return {
    ...insights,
    last_analyzed: now(),
    note: "Re-analysis triggered (demo).",
  };
}

// ── Mock chat router ────────────────────────────────────────────────────────
export function mockChat(message: string): ChatQueryResponse {
  const m = message.toLowerCase();

  if (/fraud|alert|suspicious|risk/.test(m)) {
    const high = mockState.fraudAlerts.filter((a) => (a.risk_score ?? 0) >= 0.7);
    return {
      agent_type: "fraud_agent",
      content: `I found ${high.length} high-risk alerts pending review. The top alert is ${high[0]?.alert_id} on customer ${high[0]?.customer_id} with a risk score of ${high[0]?.risk_score}.`,
      cards: high.slice(0, 3).map((a) => ({
        type: "alert",
        title: `${a.merchant} — $${a.amount}`,
        value: `risk ${a.risk_score?.toFixed(2)}`,
        subtitle: `${a.alert_id} · customer ${a.customer_id}`,
        status: a.status,
      })),
    };
  }

  if (/loan|underwrit|dti|ltv|mortgage/.test(m)) {
    const items = Object.values(mockState.loans);
    return {
      agent_type: "loan_agent",
      content: `${items.length} loan reviews are queued. ${items.filter((l) => l.recommendation === "approve_with_conditions").length} recommended for conditional approval.`,
      cards: items.map((l) => ({
        type: "summary",
        title: `${l.application_id} — ${l.recommendation}`,
        subtitle: `DTI ${(l.dti! * 100).toFixed(0)}% · LTV ${(l.ltv! * 100).toFixed(0)}%`,
        status: l.status,
      })),
    };
  }

  if (/advice|advisor|recommend|next.?best|nba/.test(m)) {
    return {
      agent_type: "advisory_agent",
      content:
        "There are 2 advisory drafts pending review. The highest-value opportunity is for cust-001 with an estimated $4,120/yr customer benefit.",
      cards: Object.values(mockState.advice).map((d) => ({
        type: "action",
        title: `Draft for ${d.customer_id}`,
        subtitle: `${(d.recommendations as string[]).length} recommendations`,
        status: d.status,
      })),
    };
  }

  if (/branch|wait time|kpi/.test(m)) {
    const sorted = [...mockState.branches].sort(
      (a, b) => (a.health_score ?? 0) - (b.health_score ?? 0),
    );
    return {
      agent_type: "branch_agent",
      content: `Lowest-performing branch is ${sorted[0].name} (health ${sorted[0].health_score}). Operational escalation recommended.`,
      cards: sorted.slice(0, 3).map((b) => ({
        type: "metric",
        title: b.name ?? b.branch_id,
        value: `${Math.round((b.health_score ?? 0) * 100)}`,
        subtitle: `${b.region} · ${b.open_issues} issues`,
        status: (b.health_score ?? 0) < 0.5 ? "at_risk" : "ok",
      })),
    };
  }

  if (/sentiment|customer feeling|nps|complain/.test(m)) {
    return {
      agent_type: "sentiment_agent",
      content:
        "1 customer is currently classified negative (cust-014). Cross-sell suppression has been auto-applied.",
      cards: Object.values(mockState.sentiment).map((s) => ({
        type: "evidence",
        title: `${s.customer_id}`,
        value: String(s.sentiment),
        subtitle: `score ${(s.score as number).toFixed(2)}`,
      })),
    };
  }

  return {
    agent_type: "router",
    content:
      "I can route to fraud, loans, advisory, branches, or sentiment agents. Try: 'show me high-risk fraud alerts', 'which branches are underperforming?', or 'what advisory drafts are pending?'",
    cards: [],
  };
}

export function mockHealth() {
  return { status: "ok", env: "demo" };
}
