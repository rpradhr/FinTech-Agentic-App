import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { endpoints, type FraudAlert, type FraudDecision, ApiError, auth } from "@/lib/api";
import { Surface, PageHeader, Chip, M3Button, TextField, EmptyState } from "@/components/m3";
import { ShieldAlert, RefreshCw, Send } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/fraud")({
  head: () => ({
    meta: [
      { title: "Fraud — FinTech Agentic" },
      { name: "description", content: "Real-time fraud alerts with HITL approval gates." },
    ],
  }),
  component: FraudPage,
});

function riskTone(score?: number): "danger" | "warning" | "info" | "success" {
  if (score == null) return "info";
  if (score >= 0.8) return "danger";
  if (score >= 0.5) return "warning";
  if (score >= 0.25) return "info";
  return "success";
}

function FraudPage() {
  const qc = useQueryClient();
  const alerts = useQuery({ queryKey: ["fraud", "alerts"], queryFn: endpoints.listFraudAlerts });
  const [selected, setSelected] = useState<string | null>(null);
  const [notes, setNotes] = useState("");

  const approve = useMutation({
    mutationFn: (vars: { id: string; decision: FraudDecision }) =>
      endpoints.approveFraud(vars.id, {
        analyst_id: auth.getUser()?.user_id ?? "analyst-1",
        decision: vars.decision,
        notes: notes || undefined,
      }),
    onSuccess: (_, v) => {
      toast.success(`Alert ${v.decision}`);
      setNotes("");
      qc.invalidateQueries({ queryKey: ["fraud"] });
    },
    onError: (e: ApiError) => toast.error(e.message),
  });

  const ingest = useMutation({
    mutationFn: () =>
      endpoints.ingestTransaction({
        transaction_id: `tx-${Date.now()}`,
        customer_id: "cust-001",
        amount: Math.round(Math.random() * 9000 + 100),
        merchant: "Demo Merchant",
        currency: "USD",
        timestamp: new Date().toISOString(),
      }),
    onSuccess: () => {
      toast.success("Transaction ingested");
      qc.invalidateQueries({ queryKey: ["fraud"] });
    },
    onError: (e: ApiError) => toast.error(e.message),
  });

  const list = alerts.data ?? [];
  const current: FraudAlert | undefined = list.find((a) => a.alert_id === selected) ?? list[0];

  return (
    <div>
      <PageHeader
        eyebrow="Fraud Workbench"
        title="Real-time fraud triage"
        subtitle="Review scored transactions and approve, decline, or escalate. Decisions write to the audit trail."
        actions={
          <>
            <M3Button
              variant="tonal"
              onClick={() => alerts.refetch()}
              disabled={alerts.isFetching}
            >
              <RefreshCw className={`h-4 w-4 ${alerts.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </M3Button>
            <M3Button onClick={() => ingest.mutate()} disabled={ingest.isPending}>
              <Send className="h-4 w-4" />
              Ingest demo TX
            </M3Button>
          </>
        }
      />

      {alerts.isError ? (
        <EmptyState
          icon={ShieldAlert}
          title="Cannot reach backend"
          description={(alerts.error as ApiError)?.message}
        />
      ) : list.length === 0 && !alerts.isLoading ? (
        <EmptyState
          icon={ShieldAlert}
          title="No fraud alerts"
          description="Ingest a transaction to generate one."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[420px_1fr]">
          <Surface tone="container" className="overflow-hidden p-0">
            <div className="border-b border-outline-variant px-4 py-3 text-sm font-semibold text-on-surface">
              Alerts ({list.length})
            </div>
            <ul className="max-h-[640px] divide-y divide-outline-variant overflow-auto">
              {alerts.isLoading
                ? Array.from({ length: 4 }).map((_, i) => (
                    <li key={i} className="animate-pulse px-4 py-4">
                      <div className="h-4 w-32 rounded bg-surface-container-highest" />
                      <div className="mt-2 h-3 w-48 rounded bg-surface-container-highest" />
                    </li>
                  ))
                : list.map((a) => {
                    const active = (current?.alert_id ?? null) === a.alert_id;
                    return (
                      <li key={a.alert_id}>
                        <button
                          onClick={() => setSelected(a.alert_id)}
                          className={`m3-state w-full px-4 py-3 text-left ${
                            active ? "bg-secondary/40" : ""
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-xs text-on-surface-variant">
                              {a.alert_id}
                            </span>
                            <Chip tone={riskTone(a.risk_score)}>
                              {a.risk_score != null ? a.risk_score.toFixed(2) : "—"}
                            </Chip>
                          </div>
                          <div className="mt-1 text-sm text-on-surface">
                            {a.merchant ?? "Unknown merchant"} · ${Number(a.amount ?? 0).toLocaleString()}
                          </div>
                          <div className="text-xs text-on-surface-variant">
                            customer {a.customer_id} · {a.status}
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
                  <Chip tone={riskTone(current.risk_score)}>
                    risk {current.risk_score?.toFixed?.(2) ?? "—"}
                  </Chip>
                  <Chip tone="info">{current.status}</Chip>
                </div>
                <h2 className="m3-headline mt-3 text-on-surface">
                  ${Number(current.amount ?? 0).toLocaleString()}{" "}
                  <span className="text-on-surface-variant">at {current.merchant ?? "—"}</span>
                </h2>
                <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  <div>
                    <dt className="text-xs text-on-surface-variant">Alert ID</dt>
                    <dd className="font-mono text-on-surface">{current.alert_id}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-on-surface-variant">Transaction</dt>
                    <dd className="font-mono text-on-surface">{current.transaction_id}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-on-surface-variant">Customer</dt>
                    <dd className="font-mono text-on-surface">{current.customer_id}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-on-surface-variant">Created</dt>
                    <dd className="text-on-surface">{current.created_at ?? "—"}</dd>
                  </div>
                </dl>
                {current.reason && (
                  <div className="mt-5 rounded-2xl border border-outline-variant bg-surface p-4 text-sm text-on-surface">
                    <div className="m3-label mb-1 text-on-surface-variant">Reason</div>
                    {current.reason}
                  </div>
                )}

                <div className="mt-6">
                  <TextField
                    label="Analyst notes (optional)"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Why are you approving / declining?"
                  />
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  <M3Button
                    variant="filled"
                    onClick={() => approve.mutate({ id: current.alert_id, decision: "approved" })}
                    disabled={approve.isPending}
                  >
                    Approve
                  </M3Button>
                  <M3Button
                    variant="danger"
                    onClick={() => approve.mutate({ id: current.alert_id, decision: "declined" })}
                    disabled={approve.isPending}
                  >
                    Decline
                  </M3Button>
                  <M3Button
                    variant="outlined"
                    onClick={() => approve.mutate({ id: current.alert_id, decision: "escalated" })}
                    disabled={approve.isPending}
                  >
                    Escalate
                  </M3Button>
                </div>
              </>
            ) : (
              <div className="text-on-surface-variant">Select an alert.</div>
            )}
          </Surface>
        </div>
      )}
    </div>
  );
}
