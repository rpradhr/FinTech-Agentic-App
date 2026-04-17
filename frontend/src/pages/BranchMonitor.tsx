import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getBranchDashboard, getBranchInsights, triggerBranchAnalysis } from "@/services/api";
import type { BranchDashboardEntry, BranchInsight } from "@/types";

// ─── helpers ────────────────────────────────────────────────────────────────

function waitTimeColor(mins: number | null | undefined): string {
  if (mins == null) return "#202124";
  if (mins > 20) return "#c5221f";
  if (mins > 15) return "#fbbc04";
  return "#202124";
}

function cardTopBorderColor(complaints: number): string {
  if (complaints > 5) return "#c5221f";
  if (complaints > 2) return "#fbbc04";
  return "#34a853";
}

// ─── BranchCard ─────────────────────────────────────────────────────────────

function BranchCard({
  branch,
  selected,
  onClick,
}: {
  branch: BranchDashboardEntry;
  selected: boolean;
  onClick: () => void;
}) {
  const borderColor = cardTopBorderColor(branch.complaint_count);
  const waitColor = waitTimeColor(branch.avg_wait_time_minutes);
  const highComplaints = branch.complaint_count > 5;
  const goodAccounts = branch.new_accounts_opened > 10;

  return (
    <button
      onClick={onClick}
      className={`md-card w-full text-left transition-all duration-200 cursor-pointer
        ${selected
          ? "ring-2 ring-[#1a73e8] bg-[#f8fbff] shadow-md-2"
          : "hover:shadow-md-2 shadow-md-1"
        }`}
      style={{ borderTop: `3px solid ${borderColor}`, padding: 0 }}
    >
      <div className="p-4">
        {/* Card header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 20, color: "#1a73e8" }}
            >
              storefront
            </span>
            <span className="font-bold text-[#202124] text-sm leading-tight">
              {branch.branch_name || branch.branch_id}
            </span>
          </div>
          <span className="text-xs text-[#5f6368]">{branch.report_date}</span>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-3 gap-2 text-center">
          {/* Wait time */}
          <div className="flex flex-col items-center">
            <span
              className="text-xl font-bold"
              style={{ color: waitColor }}
            >
              {branch.avg_wait_time_minutes != null
                ? branch.avg_wait_time_minutes.toFixed(1)
                : "—"}
            </span>
            <span className="text-xs text-[#5f6368] mt-0.5">Wait (min)</span>
          </div>

          {/* Complaints */}
          <div className="flex flex-col items-center">
            <span
              className="text-xl font-bold"
              style={
                highComplaints
                  ? {
                      color: "#c5221f",
                      background: "#fce8e6",
                      borderRadius: "999px",
                      width: 36,
                      height: 36,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }
                  : { color: "#202124" }
              }
            >
              {branch.complaint_count}
            </span>
            <span className="text-xs text-[#5f6368] mt-0.5">Complaints</span>
          </div>

          {/* Accounts opened */}
          <div className="flex flex-col items-center">
            <span
              className="text-xl font-bold"
              style={{ color: goodAccounts ? "#137333" : "#202124" }}
            >
              {branch.new_accounts_opened}
            </span>
            <span className="text-xs text-[#5f6368] mt-0.5">Accounts</span>
          </div>
        </div>
      </div>
    </button>
  );
}

// ─── BranchInsightPanel ──────────────────────────────────────────────────────

function BranchInsightPanel({ branchId }: { branchId: string }) {
  const { data: insights = [], refetch, isLoading } = useQuery<BranchInsight[]>({
    queryKey: ["branch-insights", branchId],
    queryFn: () => getBranchInsights(branchId),
  });

  const mutation = useMutation({
    mutationFn: () => triggerBranchAnalysis(branchId),
    onSuccess: () => refetch(),
  });

  return (
    <div className="md-card shadow-md-1 animate-slide-up overflow-hidden">
      {/* Panel header */}
      <div
        className="px-5 py-4 flex items-center justify-between"
        style={{ borderBottom: "1px solid #dadce0" }}
      >
        <div className="flex items-center gap-2">
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 20, color: "#1a73e8" }}
          >
            analytics
          </span>
          <h2 className="font-bold text-[#202124] text-sm">
            Insights:{" "}
            <span style={{ color: "#1a73e8" }}>{branchId}</span>
          </h2>
        </div>
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="btn-tonal text-xs"
        >
          {mutation.isPending ? (
            <span className="flex items-center gap-1">
              <span
                className="material-symbols-outlined animate-spin"
                style={{ fontSize: 14 }}
              >
                progress_activity
              </span>
              Analyzing…
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <span
                className="material-symbols-outlined"
                style={{ fontSize: 14 }}
              >
                play_arrow
              </span>
              Run Analysis
            </span>
          )}
        </button>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="px-5 py-4 space-y-4">
          {[1, 2].map((n) => (
            <div key={n} className="space-y-2">
              <div className="h-4 bg-[#f1f3f4] animate-pulse rounded w-3/4" />
              <div className="h-3 bg-[#f1f3f4] animate-pulse rounded w-full" />
              <div className="h-3 bg-[#f1f3f4] animate-pulse rounded w-5/6" />
              <div className="h-3 bg-[#f1f3f4] animate-pulse rounded w-2/3" />
            </div>
          ))}
        </div>
      )}

      {/* Insights list */}
      {!isLoading && insights.length > 0 && (
        <div>
          {insights.map((insight) => (
            <div
              key={insight.insight_id}
              className="px-5 py-4 space-y-3 animate-fade-in"
              style={{ borderBottom: "1px solid #f1f3f4" }}
            >
              {/* Issue summary */}
              <div className="flex items-start gap-2">
                <span
                  className="material-symbols-outlined mt-0.5 flex-shrink-0"
                  style={{ fontSize: 18, color: "#fbbc04" }}
                >
                  warning
                </span>
                <p className="text-sm font-bold text-[#202124]">
                  {insight.issue_summary}
                </p>
              </div>

              {/* Probable causes */}
              {insight.probable_causes.length > 0 && (
                <div className="ml-6">
                  <p
                    className="text-xs font-semibold mb-1.5"
                    style={{ color: "#5f6368" }}
                  >
                    Probable causes
                  </p>
                  <ul className="space-y-1">
                    {insight.probable_causes.map((cause, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span
                          className="mt-1.5 flex-shrink-0 rounded-full"
                          style={{
                            width: 6,
                            height: 6,
                            background: "#fbbc04",
                            display: "inline-block",
                          }}
                        />
                        <span className="text-xs text-[#202124]">{cause}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Ranked recommendations */}
              {insight.ranked_recommendations.length > 0 && (
                <div className="ml-6">
                  <p
                    className="text-xs font-semibold mb-1.5"
                    style={{ color: "#5f6368" }}
                  >
                    Recommendations
                  </p>
                  <ol className="space-y-1">
                    {insight.ranked_recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span
                          className="material-symbols-outlined flex-shrink-0"
                          style={{ fontSize: 14, color: "#34a853", marginTop: 1 }}
                        >
                          check_circle
                        </span>
                        <span className="text-xs" style={{ color: "#1a73e8" }}>
                          <span
                            className="font-semibold mr-1"
                            style={{ color: "#5f6368" }}
                          >
                            {i + 1}.
                          </span>
                          {rec}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && insights.length === 0 && (
        <div className="px-5 py-10 flex flex-col items-center gap-3 text-center">
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 48, color: "#dadce0" }}
          >
            psychology
          </span>
          <p className="text-sm font-medium text-[#5f6368]">No insights yet</p>
          <p className="text-xs text-[#5f6368] max-w-xs">
            Click "Run Analysis" to detect anomalies and get recommendations for
            this branch.
          </p>
        </div>
      )}
    </div>
  );
}

// ─── BranchMonitor (page) ────────────────────────────────────────────────────

export default function BranchMonitor() {
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);

  const { data: branches = [] } = useQuery<BranchDashboardEntry[]>({
    queryKey: ["branch-dashboard"],
    queryFn: getBranchDashboard,
    refetchInterval: 60_000,
  });

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-[#202124]">Branch Monitor</h1>
        <p className="text-sm text-[#5f6368]">
          Operational intelligence across all locations
        </p>
      </div>

      {/* Empty state */}
      {branches.length === 0 && (
        <div
          className="md-card shadow-md-1 flex flex-col items-center gap-4 py-14 text-center animate-fade-in"
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 56, color: "#dadce0" }}
          >
            store_mall_directory
          </span>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-[#5f6368]">
              No branch KPI data available
            </p>
            <p className="text-xs text-[#5f6368]">
              Run{" "}
              <code
                className="px-1.5 py-0.5 rounded text-xs font-mono"
                style={{ background: "#f1f3f4", color: "#202124" }}
              >
                ./scripts/seed.sh
              </code>{" "}
              to load sample data.
            </p>
          </div>
        </div>
      )}

      {/* Branch grid */}
      {branches.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {branches.map((b) => (
            <BranchCard
              key={b.branch_id}
              branch={b}
              selected={selectedBranch === b.branch_id}
              onClick={() => setSelectedBranch(b.branch_id)}
            />
          ))}
        </div>
      )}

      {/* Insights panel */}
      {selectedBranch && <BranchInsightPanel branchId={selectedBranch} />}
    </div>
  );
}
