import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, auth, endpoints } from "@/lib/api";
import { Surface, PageHeader, Chip, M3Button, TextField, EmptyState } from "@/components/m3";
import { HeartHandshake, Search } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/advisory")({
  head: () => ({
    meta: [
      { title: "Advisory — FinTech Agentic" },
      { name: "description", content: "Advisor-reviewed next-best-action recommendations." },
    ],
  }),
  component: AdvisoryPage,
});

function AdvisoryPage() {
  const qc = useQueryClient();
  const [customerId, setCustomerId] = useState("cust-001");
  const [submitted, setSubmitted] = useState("cust-001");
  const [edits, setEdits] = useState("");

  const draft = useQuery({
    queryKey: ["advice", submitted],
    queryFn: () => endpoints.getAdviceDraft(submitted, auth.getUser()?.user_id),
    enabled: !!submitted,
    retry: 0,
  });

  const approve = useMutation({
    mutationFn: () =>
      endpoints.approveAdvice(draft.data!.draft_id, {
        advisor_id: auth.getUser()?.user_id ?? "adv-1",
        advisor_edits: edits || null,
      }),
    onSuccess: () => {
      toast.success("Advice approved");
      setEdits("");
      qc.invalidateQueries({ queryKey: ["advice"] });
    },
    onError: (e: ApiError) => toast.error(e.message),
  });

  const d = draft.data;
  const recs = Array.isArray(d?.recommendations)
    ? d!.recommendations
    : d?.recommendations
      ? [d.recommendations as string]
      : [];

  return (
    <div>
      <PageHeader
        eyebrow="Advisory Workbench"
        title="Next-best-action drafts"
        subtitle="The advisory agent assembles a customer profile and drafts recommendations. A licensed advisor reviews and approves before delivery."
      />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted(customerId.trim());
        }}
        className="mb-6 flex flex-wrap items-end gap-3"
      >
        <TextField
          label="Customer ID"
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
          className="w-72"
        />
        <M3Button type="submit">
          <Search className="h-4 w-4" />
          Load draft
        </M3Button>
      </form>

      {draft.isError ? (
        <EmptyState
          icon={HeartHandshake}
          title="No draft available"
          description={(draft.error as ApiError)?.message}
        />
      ) : draft.isLoading ? (
        <Surface tone="container" className="h-64 animate-pulse" />
      ) : d ? (
        <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <Surface tone="container" className="p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone="primary">{d.status ?? "draft"}</Chip>
              <span className="font-mono text-xs text-on-surface-variant">{d.draft_id}</span>
            </div>
            <h2 className="m3-headline mt-3 text-on-surface">
              Recommendations for {d.customer_id}
            </h2>
            <ol className="mt-5 space-y-3">
              {recs.length === 0 && (
                <li className="text-sm text-on-surface-variant">No recommendations.</li>
              )}
              {recs.map((r, i) => (
                <li
                  key={i}
                  className="flex gap-3 rounded-2xl border border-outline-variant bg-surface p-4 text-sm text-on-surface"
                >
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-primary/12 text-xs font-bold text-primary">
                    {i + 1}
                  </span>
                  <span>{r}</span>
                </li>
              ))}
            </ol>
          </Surface>

          <Surface tone="container" className="p-6">
            <h3 className="m3-title text-on-surface">Advisor sign-off</h3>
            <p className="mt-1 text-sm text-on-surface-variant">
              Optionally edit before approving for delivery.
            </p>
            <div className="mt-4">
              <label className="text-xs font-semibold text-on-surface-variant">Advisor edits</label>
              <textarea
                value={edits}
                onChange={(e) => setEdits(e.target.value)}
                rows={6}
                className="mt-1.5 w-full rounded-xl border border-outline bg-surface p-3 text-sm text-on-surface outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                placeholder="Optional rewrite or additions..."
              />
            </div>
            <M3Button className="mt-4 w-full" onClick={() => approve.mutate()} disabled={approve.isPending}>
              Approve & release
            </M3Button>
          </Surface>
        </div>
      ) : null}
    </div>
  );
}
