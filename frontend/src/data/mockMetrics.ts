import { subDays, format } from "date-fns";

// ── Helpers ───────────────────────────────────────────────────────────────────
const days = (n: number) =>
  Array.from({ length: n }, (_, i) =>
    format(subDays(new Date(), n - 1 - i), "MMM d")
  );

// ── 14-day fraud alert trend ──────────────────────────────────────────────────
export const fraudTrend = days(14).map((date, i) => ({
  date,
  critical: Math.max(0, Math.round(4 + Math.sin(i * 0.7) * 3)),
  high:     Math.max(0, Math.round(9 + Math.cos(i * 0.5) * 4)),
  medium:   Math.max(0, Math.round(15 + Math.sin(i * 0.3) * 5)),
  cleared:  Math.max(0, Math.round(18 + Math.cos(i * 0.4) * 6)),
}));

// ── Sentiment distribution (pie) ─────────────────────────────────────────────
export const sentimentDist = [
  { name: "Positive",      value: 42, color: "#34a853" },
  { name: "Neutral",       value: 28, color: "#fbbc04" },
  { name: "Negative",      value: 22, color: "#ea4335" },
  { name: "Very Negative", value: 8,  color: "#c5221f" },
];

// ── Loan review funnel ────────────────────────────────────────────────────────
export const loanFunnel = [
  { stage: "Submitted",   count: 134, fill: "#1a73e8" },
  { stage: "In Review",   count: 89,  fill: "#1967d2" },
  { stage: "Missing Docs",count: 41,  fill: "#fbbc04" },
  { stage: "Approved",    count: 38,  fill: "#34a853" },
  { stage: "Declined",    count: 10,  fill: "#ea4335" },
];

// ── Branch performance (radar) ────────────────────────────────────────────────
export const branchRadar = [
  { metric: "Sales",       "West Side": 82, "Downtown": 74, "East Park": 61 },
  { metric: "Wait Time",   "West Side": 55, "Downtown": 78, "East Park": 88 },
  { metric: "Satisfaction","West Side": 68, "Downtown": 85, "East Park": 72 },
  { metric: "Compliance",  "West Side": 91, "Downtown": 88, "East Park": 79 },
  { metric: "Staff Util.", "West Side": 63, "Downtown": 71, "East Park": 84 },
];

// ── Agent activity (stacked bar, last 7 days) ─────────────────────────────────
export const agentActivity = days(7).map((date, i) => ({
  date,
  fraud:     Math.round(12 + Math.sin(i) * 4),
  sentiment: Math.round(18 + Math.cos(i) * 6),
  loan:      Math.round(8 + Math.sin(i * 0.8) * 3),
  branch:    Math.round(5 + Math.cos(i * 1.2) * 2),
  advisory:  Math.round(9 + Math.sin(i * 0.5) * 4),
}));

// ── KPI summary cards ─────────────────────────────────────────────────────────
export const kpiCards = [
  {
    label:   "Fraud Alerts (Pending)",
    value:   "23",
    delta:   "-12%",
    positive: true,
    color:   "#ea4335",
    icon:    "shield",
  },
  {
    label:   "Avg Review Time",
    value:   "3.2m",
    delta:   "-28%",
    positive: true,
    color:   "#1a73e8",
    icon:    "speed",
  },
  {
    label:   "Loan Triage Time",
    value:   "4.1m",
    delta:   "-41%",
    positive: true,
    color:   "#34a853",
    icon:    "trending_down",
  },
  {
    label:   "Override Rate",
    value:   "8.3%",
    delta:   "+0.4%",
    positive: false,
    color:   "#fbbc04",
    icon:    "feedback",
  },
  {
    label:   "Churn-Risk Customers",
    value:   "47",
    delta:   "+3",
    positive: false,
    color:   "#ea4335",
    icon:    "person_off",
  },
  {
    label:   "Advice Acceptance",
    value:   "67%",
    delta:   "+5%",
    positive: true,
    color:   "#34a853",
    icon:    "thumb_up",
  },
];

// ── Churn risk over time ──────────────────────────────────────────────────────
export const churnTrend = days(14).map((date, i) => ({
  date,
  high:   Math.max(0, Math.round(12 + Math.sin(i * 0.6) * 4)),
  medium: Math.max(0, Math.round(28 + Math.cos(i * 0.4) * 7)),
  low:    Math.max(0, Math.round(55 + Math.sin(i * 0.3) * 10)),
}));

// ── Model performance ─────────────────────────────────────────────────────────
export const modelPerf = [
  { agent: "Fraud",     precision: 91, recall: 87, f1: 89, latency: 2.1 },
  { agent: "Sentiment", precision: 84, recall: 82, f1: 83, latency: 1.4 },
  { agent: "Loan",      precision: 88, recall: 79, f1: 83, latency: 3.8 },
  { agent: "Branch",    precision: 76, recall: 73, f1: 74, latency: 4.2 },
  { agent: "Advisory",  precision: 72, recall: 68, f1: 70, latency: 5.1 },
];
