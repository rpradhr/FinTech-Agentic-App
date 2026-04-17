import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useNavigate, Link } from "react-router-dom";
import { fetchFraudAlerts, approveFraudAlert } from "@/services/api";
import RiskBadge from "@/components/RiskBadge";
import StatusBadge from "@/components/StatusBadge";
import type { FraudAlert } from "@/types";
import clsx from "clsx";

// ─── helpers ────────────────────────────────────────────────────────────────

type RiskLevel = "critical" | "high" | "medium" | "low";

function riskBorderColor(level: RiskLevel): string {
  switch (level) {
    case "critical": return "border-l-[#c5221f]";
    case "high":     return "border-l-[#e37400]";
    case "medium":   return "border-l-[#fbbc04]";
    default:         return "border-l-[#34a853]";
  }
}

function scoreBarColor(score: number): string {
  if (score >= 0.9) return "#c5221f";
  if (score >= 0.7) return "#e37400";
  if (score >= 0.4) return "#fbbc04";
  return "#34a853";
}

type FilterLevel = "all" | RiskLevel;

const FILTER_LABELS: { value: FilterLevel; label: string }[] = [
  { value: "all",      label: "All" },
  { value: "critical", label: "Critical" },
  { value: "high",     label: "High" },
  { value: "medium",   label: "Medium" },
  { value: "low",      label: "Low" },
];

// ─── FraudAlertList ──────────────────────────────────────────────────────────

export function FraudAlertList() {
  const [filter, setFilter] = useState<FilterLevel>("all");
  const [sortField, setSortField] = useState<"risk_score" | "alert_id">("risk_score");
  const [sortAsc, setSortAsc] = useState(false);

  const { data: alerts = [], isLoading } = useQuery<FraudAlert[]>({
    queryKey: ["fraud-alerts"],
    queryFn: fetchFraudAlerts,
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div className="p-8 flex items-center gap-3 text-[#5f6368]">
        <span className="material-symbols-outlined animate-spin text-[#1a73e8]">progress_activity</span>
        Loading alerts…
      </div>
    );
  }

  const filtered = alerts.filter((a) => filter === "all" || a.risk_level === filter);
  const sorted = [...filtered].sort((a, b) => {
    const dir = sortAsc ? 1 : -1;
    if (sortField === "risk_score") return (a.risk_score - b.risk_score) * dir;
    return a.alert_id.localeCompare(b.alert_id) * dir;
  });

  function toggleSort(field: typeof sortField) {
    if (sortField === field) setSortAsc((v) => !v);
    else { setSortField(field); setSortAsc(false); }
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[28px] font-medium tracking-tight text-[#202124]">
            Fraud Workbench
          </h1>
          <p className="text-sm text-[#5f6368] mt-0.5">
            {alerts.length} total alert{alerts.length !== 1 ? "s" : ""} · {alerts.filter(a => a.status === "pending_analyst_review").length} pending review
          </p>
        </div>
        <span className="material-symbols-outlined text-[#1a73e8] text-3xl">security</span>
      </div>

      {/* Filter chip row */}
      <div className="flex items-center gap-2 flex-wrap">
        {FILTER_LABELS.map(({ value, label }) => {
          const count = value === "all" ? alerts.length : alerts.filter(a => a.risk_level === value).length;
          return (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={clsx(
                "chip transition-all",
                filter === value
                  ? "bg-[#1a73e8] text-white border-[#1a73e8]"
                  : "bg-transparent text-[#5f6368] border-[#dadce0] hover:bg-[#e8f0fe] hover:border-[#1a73e8] hover:text-[#1a73e8]"
              )}
            >
              {label}
              <span className={clsx(
                "ml-1.5 text-xs font-semibold rounded-full px-1.5 py-0.5",
                filter === value ? "bg-white/20 text-white" : "bg-[#f1f3f4] text-[#5f6368]"
              )}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Table card */}
      <div className="md-card overflow-hidden shadow-md-1">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#f8f9fa] border-b border-[#dadce0]">
              {[
                { key: "alert_id",   label: "Alert ID",  sortable: true },
                { key: "customer",   label: "Customer",  sortable: false },
                { key: "risk",       label: "Risk",      sortable: false },
                { key: "risk_score", label: "Score",     sortable: true },
                { key: "reasons",    label: "Reasons",   sortable: false },
                { key: "status",     label: "Status",    sortable: false },
                { key: "action",     label: "",          sortable: false },
              ].map((col) => (
                <th
                  key={col.key}
                  className={clsx(
                    "px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wide select-none",
                    col.sortable && "cursor-pointer hover:text-[#202124]"
                  )}
                  onClick={col.sortable ? () => toggleSort(col.key as typeof sortField) : undefined}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {col.sortable && sortField === col.key && (
                      <span className="material-symbols-outlined text-xs">
                        {sortAsc ? "arrow_upward" : "arrow_downward"}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#dadce0]">
            {sorted.map((alert) => {
              const pct = Math.round(alert.risk_score * 100);
              return (
                <tr
                  key={alert.alert_id}
                  className={clsx(
                    "hover:bg-[#f8f9fa] transition-colors border-l-4",
                    riskBorderColor(alert.risk_level as RiskLevel)
                  )}
                >
                  {/* Alert ID */}
                  <td className="px-4 py-3 font-mono text-xs text-[#202124]">{alert.alert_id}</td>

                  {/* Customer */}
                  <td className="px-4 py-3 text-[#202124]">{alert.customer_id}</td>

                  {/* Risk badge */}
                  <td className="px-4 py-3">
                    <RiskBadge level={alert.risk_level} />
                  </td>

                  {/* Score with mini progress bar */}
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1 min-w-[64px]">
                      <span className="text-xs font-semibold text-[#202124]">{pct}%</span>
                      <div className="w-full h-1.5 rounded-full bg-[#dadce0] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${pct}%`, backgroundColor: scoreBarColor(alert.risk_score) }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Reason chips */}
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1 max-w-[220px]">
                      {alert.reasons.slice(0, 2).map((r) => (
                        <span
                          key={r}
                          className="chip text-xs bg-[#fce8e6] text-[#c5221f] border-[#f28b82] py-0.5 px-2"
                        >
                          {r.replace(/_/g, " ")}
                        </span>
                      ))}
                      {alert.reasons.length > 2 && (
                        <span className="chip text-xs bg-[#f1f3f4] text-[#5f6368] border-[#dadce0] py-0.5 px-2">
                          +{alert.reasons.length - 2}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3">
                    <StatusBadge status={alert.status} />
                  </td>

                  {/* Review action */}
                  <td className="px-4 py-3">
                    <Link to={`/fraud/${alert.alert_id}`}>
                      <button className="btn-tonal text-xs py-1.5 px-3 inline-flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm">manage_search</span>
                        Review
                      </button>
                    </Link>
                  </td>
                </tr>
              );
            })}

            {sorted.length === 0 && (
              <tr>
                <td colSpan={7}>
                  <div className="flex flex-col items-center gap-3 py-16 text-[#5f6368]">
                    <span className="material-symbols-outlined text-5xl text-[#dadce0]">verified_user</span>
                    <p className="text-sm font-medium">
                      {filter === "all"
                        ? "No pending alerts. The fraud queue is clear."
                        : `No ${filter} alerts at this time.`}
                    </p>
                    {filter !== "all" && (
                      <button
                        className="btn-outlined text-xs py-1 px-3"
                        onClick={() => setFilter("all")}
                      >
                        Show all alerts
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── FraudAlertDetail ────────────────────────────────────────────────────────

export function FraudAlertDetail() {
  const { alertId } = useParams<{ alertId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState("");
  const [decision, setDecision] = useState<"approved" | "declined" | "escalated">("declined");

  const { data: alerts = [] } = useQuery<FraudAlert[]>({
    queryKey: ["fraud-alerts"],
    queryFn: fetchFraudAlerts,
  });
  const alert = alerts.find((a) => a.alert_id === alertId);

  const mutation = useMutation({
    mutationFn: () =>
      approveFraudAlert(alertId!, "analyst-001", decision, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fraud-alerts"] });
      navigate("/fraud");
    },
  });

  // ── not found ──
  if (!alert) {
    return (
      <div className="p-6 animate-fade-in">
        <Link
          to="/fraud"
          className="inline-flex items-center gap-1 text-sm text-[#1a73e8] hover:underline font-medium"
        >
          <span className="material-symbols-outlined text-base">arrow_back</span>
          Fraud Workbench
        </Link>
        <div className="mt-8 flex flex-col items-center gap-3 text-[#5f6368]">
          <span className="material-symbols-outlined text-5xl text-[#dadce0]">search_off</span>
          <p className="text-sm">Alert not found or not yet loaded.</p>
        </div>
      </div>
    );
  }

  const pct = Math.round(alert.risk_score * 100);

  return (
    <div className="p-6 space-y-5 max-w-4xl animate-slide-up">
      {/* Breadcrumb */}
      <Link
        to="/fraud"
        className="inline-flex items-center gap-1 text-sm text-[#1a73e8] hover:underline font-medium"
      >
        <span className="material-symbols-outlined text-base">arrow_back</span>
        Fraud Workbench
      </Link>

      {/* Alert header card */}
      <div className="md-card p-5 shadow-md-2 space-y-4">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-[#5f6368] mb-1">Alert ID</p>
            <h1 className="text-2xl font-semibold text-[#202124] font-mono">{alert.alert_id}</h1>
            <p className="text-sm text-[#5f6368] mt-1">
              <span className="inline-flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">receipt_long</span>
                Txn: {alert.txn_id}
              </span>
              <span className="mx-2 text-[#dadce0]">·</span>
              <span className="inline-flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">person</span>
                Customer: {alert.customer_id}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <RiskBadge level={alert.risk_level} />
            <StatusBadge status={alert.status} />
          </div>
        </div>

        {/* Animated risk score bar */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[#5f6368]">Risk Score</span>
            <span
              className="text-2xl font-bold tabular-nums"
              style={{ color: scoreBarColor(alert.risk_score) }}
            >
              {pct}%
            </span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-[#dadce0] overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${pct}%`, backgroundColor: scoreBarColor(alert.risk_score) }}
            />
          </div>
        </div>
      </div>

      {/* Risk Reasons */}
      <div className="md-card p-5 shadow-md-1 space-y-3">
        <h2 className="text-base font-medium text-[#202124] flex items-center gap-2">
          <span className="material-symbols-outlined text-[#fbbc04]">warning</span>
          Risk Reasons
        </h2>
        <div className="flex flex-wrap gap-2">
          {alert.reasons.map((r) => (
            <span
              key={r}
              className="chip bg-[#fce8e6] text-[#c5221f] border-[#f28b82] inline-flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-sm">warning</span>
              {r.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      </div>

      {/* AI Explanation */}
      {alert.ai_explanation && (
        <div className="md-card p-5 shadow-md-1 space-y-3">
          <h2 className="text-base font-medium text-[#202124] flex items-center gap-2">
            <span className="material-symbols-outlined text-[#1a73e8]">smart_toy</span>
            AI Explanation
          </h2>
          <blockquote className="border-l-4 border-[#1a73e8] pl-4 italic text-sm text-[#5f6368] leading-relaxed">
            {alert.ai_explanation}
          </blockquote>
        </div>
      )}

      {/* Recommended Action */}
      <div className="md-card p-5 shadow-md-1">
        <h2 className="text-base font-medium text-[#202124] flex items-center gap-2 mb-2">
          <span className="material-symbols-outlined text-[#34a853]">task_alt</span>
          Recommended Action
        </h2>
        <p className="text-sm font-semibold text-[#202124] font-mono">
          {alert.recommended_action.replace(/_/g, " ")}
        </p>
      </div>

      {/* HITL approval gate — pending */}
      {alert.status === "pending_analyst_review" && (
        <div
          className="md-card p-5 space-y-5 shadow-md-2"
          style={{ borderLeft: "4px solid #fbbc04", backgroundColor: "#fffde7" }}
        >
          <div>
            <h2 className="text-base font-semibold text-[#202124] flex items-center gap-2">
              <span className="material-symbols-outlined text-[#fbbc04]">gavel</span>
              Analyst Decision Required
            </h2>
            <p className="text-xs text-[#5f6368] mt-1">
              This action cannot be taken automatically. You must approve, decline, or escalate.
            </p>
          </div>

          {/* Decision select */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-[#202124]">Decision</label>
            <select
              value={decision}
              onChange={(e) => setDecision(e.target.value as typeof decision)}
              className="md-input w-full"
            >
              <option value="declined">Decline — clear alert</option>
              <option value="approved">Approve — confirm fraud</option>
              <option value="escalated">Escalate to compliance</option>
            </select>
          </div>

          {/* Notes textarea */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-[#202124]">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Document your reasoning…"
              className="md-input w-full resize-none"
            />
          </div>

          {/* Submit */}
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="btn-filled disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
          >
            {mutation.isPending
              ? <><span className="material-symbols-outlined animate-spin text-sm">progress_activity</span>Submitting…</>
              : <><span className="material-symbols-outlined text-sm">check_circle</span>Submit Decision</>
            }
          </button>

          {/* Error state */}
          {mutation.isError && (
            <div
              className="flex items-start gap-2 rounded-xl px-4 py-3 text-sm"
              style={{ backgroundColor: "#fce8e6", color: "#c5221f", border: "1px solid #f28b82" }}
            >
              <span className="material-symbols-outlined text-base mt-0.5">error</span>
              <span>Failed to submit decision. Please try again.</span>
            </div>
          )}
        </div>
      )}

      {/* Already-decided state */}
      {alert.status !== "pending_analyst_review" && (
        <div
          className="md-card p-5 flex items-start gap-3 shadow-md-1"
          style={{ backgroundColor: "#e6f4ea", border: "1px solid #81c995" }}
        >
          <span className="material-symbols-outlined text-[#34a853] text-2xl mt-0.5">check_circle</span>
          <div>
            <p className="text-sm font-semibold text-[#202124]">Decision already recorded</p>
            <p className="text-xs text-[#5f6368] mt-0.5">
              This alert has been marked as <strong>{alert.status.replace(/_/g, " ")}</strong> and no further action is needed.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
