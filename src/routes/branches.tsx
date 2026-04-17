import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, endpoints, type BranchSummary } from "@/lib/api";
import { Surface, PageHeader, Chip, M3Button, EmptyState } from "@/components/m3";
import { Building2, RefreshCw, Sparkles } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/branches")({
  head: () => ({
    meta: [
      { title: "Branches — FinTech Agentic" },
      { name: "description", content: "Branch KPI monitoring and AI recommendations." },
    ],
  }),
  component: BranchesPage,
});

function healthTone(score?: number): "danger" | "warning" | "success" | "info" {
  if (score == null) return "info";
  if (score >= 0.75) return "success";
  if (score >= 0.5) return "warning";
  return "danger";
}

function BranchesPage() {
  const qc = useQueryClient();
  const dash = useQuery({
    queryKey: ["branches", "dashboard"],
    queryFn: endpoints.branchDashboard,
    retry: 0,
  });
  const [selected, setSelected] = useState<string | null>(null);

  const list = dash.data ?? [];
  const current: BranchSummary | undefined =
    list.find((b) => b.branch_id === selected) ?? list[0];

  const insights = useQuery({
    queryKey: ["branch", current?.branch_id, "insights"],
    queryFn: () => endpoints.branchInsights(current!.branch_id),
    enabled: !!current,
    retry: 0,
  });

  const analyze = useMutation({
    mutationFn: () => endpoints.analyzeBranch(current!.branch_id),
    onSuccess: () => {
      toast.success("Analysis triggered");
      qc.invalidateQueries({ queryKey: ["branch", current?.branch_id] });
    },
    onError: (e: ApiError) => toast.error(e.message),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Branch Workbench"
        title="Branch performance"
        subtitle="KPI timeseries summarized per branch with ranked operational recommendations."
        actions={
          <M3Button variant="tonal" onClick={() => dash.refetch()} disabled={dash.isFetching}>
            <RefreshCw className={`h-4 w-4 ${dash.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </M3Button>
        }
      />

      {dash.isError ? (
        <EmptyState
          icon={Building2}
          title="Cannot load branches"
          description={(dash.error as ApiError)?.message}
        />
      ) : list.length === 0 && !dash.isLoading ? (
        <EmptyState icon={Building2} title="No branches" />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[420px_1fr]">
          <Surface tone="container" className="overflow-hidden p-0">
            <div className="border-b border-outline-variant px-4 py-3 text-sm font-semibold">
              Branches ({list.length})
            </div>
            <ul className="max-h-[640px] divide-y divide-outline-variant overflow-auto">
              {list.map((b) => {
                const active = (current?.branch_id ?? null) === b.branch_id;
                return (
                  <li key={b.branch_id}>
                    <button
                      onClick={() => setSelected(b.branch_id)}
                      className={`m3-state w-full px-4 py-3 text-left ${
                        active ? "bg-secondary/40" : ""
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-on-surface">
                          {b.name ?? b.branch_id}
                        </span>
                        <Chip tone={healthTone(b.health_score)}>
                          {b.health_score != null ? Math.round(b.health_score * 100) : "—"}
                        </Chip>
                      </div>
                      <div className="text-xs text-on-surface-variant">
                        {b.region ?? "—"} · {b.open_issues ?? 0} issues
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </Surface>

          <Surface tone="container" className="p-6">
            {current ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <Chip tone={healthTone(current.health_score)}>
                    health {current.health_score?.toFixed?.(2) ?? "—"}
                  </Chip>
                  {current.region && <Chip tone="info">{current.region}</Chip>}
                </div>
                <h2 className="m3-headline mt-3 text-on-surface">
                  {current.name ?? current.branch_id}
                </h2>
                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <Stat label="Avg wait" value={`${current.wait_time_avg ?? "—"} min`} />
                  <Stat label="Open issues" value={String(current.open_issues ?? 0)} />
                  <Stat label="Branch ID" value={current.branch_id} mono />
                </div>

                <div className="mt-6 flex items-center justify-between">
                  <h3 className="m3-title text-on-surface">Insights</h3>
                  <M3Button
                    variant="tonal"
                    size="sm"
                    onClick={() => analyze.mutate()}
                    disabled={analyze.isPending}
                  >
                    <Sparkles className="h-4 w-4" />
                    Re-analyze
                  </M3Button>
                </div>
                <pre className="mt-3 max-h-96 overflow-auto rounded-2xl border border-outline-variant bg-surface p-4 text-xs text-on-surface">
                  {insights.isLoading
                    ? "Loading..."
                    : insights.isError
                      ? `Error: ${(insights.error as ApiError).message}`
                      : JSON.stringify(insights.data ?? {}, null, 2)}
                </pre>
              </>
            ) : null}
          </Surface>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-2xl border border-outline-variant bg-surface p-3">
      <div className="m3-label text-on-surface-variant">{label}</div>
      <div className={`mt-1 text-lg font-semibold text-on-surface ${mono ? "font-mono" : ""}`}>
        {value}
      </div>
    </div>
  );
}
