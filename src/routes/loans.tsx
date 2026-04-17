import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, auth, endpoints } from "@/lib/api";
import { Surface, PageHeader, Chip, M3Button, TextField, EmptyState } from "@/components/m3";
import { Landmark, Search } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/loans")({
  head: () => ({
    meta: [
      { title: "Loans — FinTech Agentic" },
      { name: "description", content: "AI-assisted loan underwriting reviews with HITL sign-off." },
    ],
  }),
  component: LoansPage,
});

function LoansPage() {
  const qc = useQueryClient();
  const [appId, setAppId] = useState("loan-001");
  const [submitted, setSubmitted] = useState<string>("loan-001");
  const [notes, setNotes] = useState("");

  const review = useQuery({
    queryKey: ["loan", submitted],
    queryFn: () => endpoints.getLoanReview(submitted),
    enabled: !!submitted,
    retry: 0,
  });

  const decide = useMutation({
    mutationFn: (decision: string) =>
      endpoints.decideLoan(submitted, {
        underwriter_id: auth.getUser()?.user_id ?? "uw-1",
        decision,
        notes: notes || undefined,
      }),
    onSuccess: (_, d) => {
      toast.success(`Loan ${d}`);
      setNotes("");
      qc.invalidateQueries({ queryKey: ["loan"] });
    },
    onError: (e: ApiError) => toast.error(e.message),
  });

  const r = review.data;

  return (
    <div>
      <PageHeader
        eyebrow="Loan Workbench"
        title="Underwriting review"
        subtitle="Pull an AI underwriting pass for an application, then approve, decline, or request changes."
      />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted(appId.trim());
        }}
        className="mb-6 flex flex-wrap items-end gap-3"
      >
        <TextField
          label="Application ID"
          value={appId}
          onChange={(e) => setAppId(e.target.value)}
          className="w-72"
        />
        <M3Button type="submit" variant="filled">
          <Search className="h-4 w-4" />
          Load review
        </M3Button>
      </form>

      {review.isError ? (
        <EmptyState
          icon={Landmark}
          title="Could not load application"
          description={(review.error as ApiError)?.message}
        />
      ) : review.isLoading ? (
        <Surface tone="container" className="h-64 animate-pulse" />
      ) : r ? (
        <div className="grid gap-4 lg:grid-cols-[1fr_420px]">
          <Surface tone="container" className="p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone="primary">{r.recommendation ?? "review"}</Chip>
              {r.status && <Chip tone="info">{r.status}</Chip>}
            </div>
            <h2 className="m3-headline mt-3 text-on-surface">Application {r.application_id}</h2>
            <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Metric label="DTI" value={r.dti != null ? `${(r.dti * 100).toFixed(1)}%` : "—"} />
              <Metric label="LTV" value={r.ltv != null ? `${(r.ltv * 100).toFixed(1)}%` : "—"} />
              <Metric label="Customer" value={r.customer_id ?? "—"} mono />
            </dl>
            {r.rationale && (
              <div className="mt-6 rounded-2xl border border-outline-variant bg-surface p-4 text-sm text-on-surface">
                <div className="m3-label mb-1 text-on-surface-variant">Rationale</div>
                {r.rationale}
              </div>
            )}
            <details className="mt-4 text-xs text-on-surface-variant">
              <summary className="cursor-pointer">Raw payload</summary>
              <pre className="mt-2 max-h-64 overflow-auto rounded-xl bg-surface p-3">
                {JSON.stringify(r, null, 2)}
              </pre>
            </details>
          </Surface>

          <Surface tone="container" className="p-6">
            <h3 className="m3-title text-on-surface">Underwriter decision</h3>
            <p className="mt-1 text-sm text-on-surface-variant">
              All decisions are written to the audit trail.
            </p>
            <div className="mt-4">
              <TextField
                label="Notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Conditions, follow-ups, etc."
              />
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <M3Button onClick={() => decide.mutate("approved")} disabled={decide.isPending}>
                Approve
              </M3Button>
              <M3Button
                variant="danger"
                onClick={() => decide.mutate("declined")}
                disabled={decide.isPending}
              >
                Decline
              </M3Button>
              <M3Button
                variant="outlined"
                onClick={() => decide.mutate("request_changes")}
                disabled={decide.isPending}
              >
                Request changes
              </M3Button>
            </div>
          </Surface>
        </div>
      ) : null}
    </div>
  );
}

function Metric({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-2xl border border-outline-variant bg-surface p-4">
      <div className="m3-label text-on-surface-variant">{label}</div>
      <div className={`mt-1 text-xl font-semibold text-on-surface ${mono ? "font-mono" : ""}`}>
        {value}
      </div>
    </div>
  );
}
