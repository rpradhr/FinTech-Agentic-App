import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, endpoints } from "@/lib/api";
import { Surface, PageHeader, M3Button, TextField, EmptyState, Chip } from "@/components/m3";
import { MessageSquareHeart, Search } from "lucide-react";

export const Route = createFileRoute("/sentiment")({
  head: () => ({
    meta: [
      { title: "Sentiment — FinTech Agentic" },
      { name: "description", content: "Customer interaction sentiment signals." },
    ],
  }),
  component: SentimentPage,
});

function SentimentPage() {
  const [customerId, setCustomerId] = useState("cust-001");
  const [submitted, setSubmitted] = useState("cust-001");

  const signal = useQuery({
    queryKey: ["sentiment", submitted],
    queryFn: () => endpoints.getCustomerSignal(submitted),
    enabled: !!submitted,
    retry: 0,
  });

  const data = signal.data as Record<string, unknown> | undefined;
  const sentiment = (data?.sentiment as string | undefined) ?? (data?.label as string | undefined);
  const score = data?.score as number | undefined;
  const recent = (data?.recent as Record<string, unknown>[] | undefined) ?? [];

  const tone =
    sentiment?.toLowerCase().includes("negative") || (score != null && score < 0)
      ? "danger"
      : sentiment?.toLowerCase().includes("positive") || (score != null && score > 0.3)
        ? "success"
        : "warning";

  return (
    <div>
      <PageHeader
        eyebrow="Sentiment Workbench"
        title="Customer signal"
        subtitle="Interactions classified to surface at-risk relationships and suppress cross-sell when appropriate."
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
          Load signal
        </M3Button>
      </form>

      {signal.isError ? (
        <EmptyState
          icon={MessageSquareHeart}
          title="No signal available"
          description={(signal.error as ApiError)?.message}
        />
      ) : signal.isLoading ? (
        <Surface tone="container" className="h-64 animate-pulse" />
      ) : data ? (
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          <Surface tone="container" className="p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone={tone}>{sentiment ?? "unknown"}</Chip>
              {score != null && <Chip tone="info">score {Number(score).toFixed(2)}</Chip>}
            </div>
            <h2 className="m3-headline mt-3 text-on-surface">Customer {submitted}</h2>
            <pre className="mt-5 max-h-96 overflow-auto rounded-2xl border border-outline-variant bg-surface p-4 text-xs text-on-surface">
              {JSON.stringify(data, null, 2)}
            </pre>
          </Surface>

          <Surface tone="container" className="p-6">
            <h3 className="m3-title text-on-surface">Recent interactions</h3>
            {recent.length === 0 ? (
              <p className="mt-2 text-sm text-on-surface-variant">
                No structured "recent" array on this signal payload.
              </p>
            ) : (
              <ul className="mt-3 space-y-2">
                {recent.map((it, i) => (
                  <li
                    key={i}
                    className="rounded-xl border border-outline-variant bg-surface p-3 text-sm text-on-surface"
                  >
                    <pre className="overflow-auto text-xs">{JSON.stringify(it, null, 2)}</pre>
                  </li>
                ))}
              </ul>
            )}
          </Surface>
        </div>
      ) : null}
    </div>
  );
}
