import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { fetchFraudAlerts, getOpenCases, getAgentMetrics } from "@/services/api";
import RiskBadge from "@/components/RiskBadge";
import StatusBadge from "@/components/StatusBadge";
import type { FraudAlert, Case } from "@/types";
import { kpiCards } from "@/data/mockMetrics";

// ── Mini stat card ────────────────────────────────────────────────────────────
function StatCard({
  label, value, delta, positive, color, icon, to,
}: {
  label: string; value: string | number; delta?: string;
  positive?: boolean; color: string; icon: string; to: string;
}) {
  return (
    <Link
      to={to}
      className="md-card p-5 hover:shadow-md-2 transition-all duration-200 group
        hover:-translate-y-0.5 flex flex-col gap-3"
    >
      <div className="flex items-start justify-between">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center"
          style={{ background: `${color}18` }}
        >
          <span
            className="material-symbols-outlined text-[20px]"
            style={{ color }}
          >
            {icon}
          </span>
        </div>
        {delta && (
          <span
            className={`text-[11px] font-medium px-2 py-0.5 rounded-full
              ${positive ? "bg-[#e6f4ea] text-[#137333]" : "bg-[#fce8e6] text-[#c5221f]"}`}
          >
            {delta}
          </span>
        )}
      </div>
      <div>
        <p className="text-2xl font-semibold text-[#202124] leading-none mb-1">
          {value}
        </p>
        <p className="text-xs text-[#5f6368]">{label}</p>
      </div>
    </Link>
  );
}

// ── Quick action card ─────────────────────────────────────────────────────────
function QuickAction({
  icon, label, description, to, color,
}: {
  icon: string; label: string; description: string; to: string; color: string;
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-4 p-4 rounded-xl border border-[#e0e0e0]
        hover:border-[#1a73e8] hover:bg-[#f8fbff] transition-all duration-150 group"
    >
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}18` }}
      >
        <span className="material-symbols-outlined text-[20px]" style={{ color }}>
          {icon}
        </span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[#202124] group-hover:text-[#1a73e8]
          transition-colors">
          {label}
        </p>
        <p className="text-xs text-[#9aa0a6] truncate">{description}</p>
      </div>
      <span className="material-symbols-outlined text-[18px] text-[#dadce0]
        group-hover:text-[#1a73e8] transition-colors">
        arrow_forward
      </span>
    </Link>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function OperationsHome() {
  const navigate = useNavigate();

  const { data: alerts = [] } = useQuery<FraudAlert[]>({
    queryKey: ["fraud-alerts"],
    queryFn: fetchFraudAlerts,
    refetchInterval: 30_000,
  });
  const { data: cases = [] } = useQuery<Case[]>({
    queryKey: ["open-cases"],
    queryFn: () => getOpenCases(),
  });
  const { data: metrics } = useQuery({
    queryKey: ["agent-metrics"],
    queryFn: getAgentMetrics,
  });

  const criticalAlerts = alerts.filter((a) => a.risk_level === "critical");
  const highAlerts     = alerts.filter((a) => a.risk_level === "high");
  const priorityAlerts = [...criticalAlerts, ...highAlerts].slice(0, 6);

  // Live-aware KPI values (prefer API, fall back to mock)
  const liveKpis = kpiCards.map((k) => {
    if (k.label === "Fraud Alerts (Pending)" && metrics?.fraud_alerts_pending !== undefined)
      return { ...k, value: String(metrics.fraud_alerts_pending) };
    return k;
  });

  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto animate-fade-in">

      {/* ── Page header ─────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-normal text-[#202124]">
            Operations Home
          </h1>
          <p className="text-sm text-[#5f6368] mt-0.5">
            {new Date().toLocaleDateString("en-US", {
              weekday: "long", year: "numeric", month: "long", day: "numeric",
            })}
          </p>
        </div>

        <div className="flex gap-2">
          <Link
            to="/dashboard"
            className="btn-tonal text-sm flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]">bar_chart</span>
            Dashboard
          </Link>
          <Link
            to="/chat"
            className="btn-filled text-sm flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]">smart_toy</span>
            Ask AI
          </Link>
        </div>
      </div>

      {/* ── KPI grid ────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-medium text-[#5f6368] uppercase tracking-wider mb-3">
          Key Metrics
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          {liveKpis.map((k) => (
            <StatCard
              key={k.label}
              label={k.label}
              value={k.value}
              delta={k.delta}
              positive={k.positive}
              color={k.color}
              icon={k.icon}
              to={
                k.label.includes("Fraud") ? "/fraud"
                : k.label.includes("Loan") ? "/loans"
                : k.label.includes("Churn") ? "/chat"
                : "/dashboard"
              }
            />
          ))}
        </div>
      </section>

      {/* ── Two-column content ───────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* High-priority alerts (2/3 width) */}
        <section className="lg:col-span-2 md-card overflow-hidden">
          <div className="px-5 py-4 border-b border-[#e0e0e0] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[#c5221f] text-[20px]">
                security
              </span>
              <h2 className="text-sm font-semibold text-[#202124]">
                High-Priority Fraud Alerts
              </h2>
              {criticalAlerts.length > 0 && (
                <span className="w-5 h-5 rounded-full bg-[#c5221f] text-white
                  text-[10px] font-bold flex items-center justify-center">
                  {criticalAlerts.length}
                </span>
              )}
            </div>
            <Link
              to="/fraud"
              className="text-xs text-[#1a73e8] hover:underline flex items-center gap-1"
            >
              View all
              <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </Link>
          </div>

          {priorityAlerts.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <span className="material-symbols-outlined text-[48px] text-[#dadce0]">
                verified_user
              </span>
              <p className="text-sm text-[#9aa0a6] mt-2">
                No high-priority alerts — connect backend for live data.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[#f1f3f4]">
              {priorityAlerts.map((alert) => (
                <Link
                  key={alert.alert_id}
                  to={`/fraud/${alert.alert_id}`}
                  className="flex items-center gap-4 px-5 py-3.5
                    hover:bg-[#f8f9fa] transition-colors group"
                >
                  <RiskBadge level={alert.risk_level} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#202124]
                      group-hover:text-[#1a73e8] transition-colors truncate">
                      {alert.alert_id}
                    </p>
                    <p className="text-xs text-[#9aa0a6] truncate">
                      {alert.customer_id} · {alert.reasons.slice(0, 2).join(", ")}
                    </p>
                  </div>
                  <StatusBadge status={alert.status} />
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Right column: open cases + quick actions */}
        <div className="space-y-6">

          {/* Open cases */}
          <section className="md-card overflow-hidden">
            <div className="px-5 py-4 border-b border-[#e0e0e0] flex items-center
              justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#1a73e8] text-[20px]">
                  folder_open
                </span>
                <h2 className="text-sm font-semibold text-[#202124]">Open Cases</h2>
              </div>
              <Link
                to="/audit"
                className="text-xs text-[#1a73e8] hover:underline"
              >
                View all
              </Link>
            </div>

            {cases.length === 0 ? (
              <p className="px-5 py-4 text-sm text-[#9aa0a6]">No open cases.</p>
            ) : (
              <div className="divide-y divide-[#f1f3f4]">
                {cases.slice(0, 4).map((c) => (
                  <div key={c.case_id} className="flex items-center gap-3 px-5 py-3">
                    <span className="text-[10px] bg-[#e8f0fe] text-[#1a73e8] px-2
                      py-0.5 rounded-full font-medium uppercase tracking-wide flex-shrink-0">
                      {c.case_type}
                    </span>
                    <p className="flex-1 text-xs text-[#202124] truncate">{c.title}</p>
                    <StatusBadge status={c.status} />
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Quick navigation */}
          <section>
            <h2 className="text-xs font-medium text-[#5f6368] uppercase tracking-wider mb-3
              px-1">
              Quick Access
            </h2>
            <div className="space-y-2">
              <QuickAction
                icon="search"
                label="Fraud Workbench"
                description="Review & approve fraud alerts"
                to="/fraud"
                color="#c5221f"
              />
              <QuickAction
                icon="account_balance"
                label="Loan Reviews"
                description="Triage pending applications"
                to="/loans"
                color="#1a73e8"
              />
              <QuickAction
                icon="tips_and_updates"
                label="Advisory Workspace"
                description="Approve customer advice packs"
                to="/advisory"
                color="#7b2d8b"
              />
              <QuickAction
                icon="storefront"
                label="Branch Monitor"
                description="Operational anomalies"
                to="/branches"
                color="#137333"
              />
              <QuickAction
                icon="receipt_long"
                label="Audit Console"
                description="Full agent trace log"
                to="/audit"
                color="#5f6368"
              />
            </div>
          </section>
        </div>
      </div>

      {/* ── AI Agent status strip ─────────────────────────────────── */}
      <section className="md-card p-5">
        <h2 className="text-sm font-semibold text-[#202124] mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-[#1a73e8] text-[20px]">hub</span>
          Agent Status
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {[
            { name: "Fraud Agent",     icon: "security",        color: "#c5221f", status: "active" },
            { name: "Sentiment Agent", icon: "sentiment_very_dissatisfied", color: "#e37400", status: "active" },
            { name: "Loan Agent",      icon: "account_balance", color: "#1a73e8", status: "active" },
            { name: "Branch Monitor",  icon: "storefront",      color: "#137333", status: "active" },
            { name: "Advisory Agent",  icon: "tips_and_updates",color: "#7b2d8b", status: "active" },
          ].map((agent) => (
            <div
              key={agent.name}
              className="flex items-center gap-3 p-3 rounded-xl bg-[#f8f9fa]
                border border-[#e0e0e0]"
            >
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ background: `${agent.color}18` }}
              >
                <span
                  className="material-symbols-outlined text-[16px]"
                  style={{ color: agent.color }}
                >
                  {agent.icon}
                </span>
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-[#202124] truncate">{agent.name}</p>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#34a853] animate-pulse" />
                  <span className="text-[10px] text-[#34a853]">Active</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t border-[#e0e0e0] flex items-center
          justify-between">
          <p className="text-xs text-[#9aa0a6]">
            All agents healthy · Supervisor orchestration online
          </p>
          <button
            onClick={() => navigate("/chat")}
            className="btn-tonal text-xs flex items-center gap-1.5"
          >
            <span className="material-symbols-outlined text-[14px]">smart_toy</span>
            Ask an Agent
          </button>
        </div>
      </section>
    </div>
  );
}
