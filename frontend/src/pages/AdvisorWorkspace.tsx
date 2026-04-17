import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAdviceDraft, approveAdviceDraft } from "@/services/api";
import StatusBadge from "@/components/StatusBadge";
import type { AdviceDraft } from "@/types";

export default function AdvisorWorkspace() {
  const [customerId, setCustomerId] = useState("");
  const [loadId, setLoadId] = useState("");

  return (
    <div className="p-6 space-y-6 max-w-4xl animate-fade-in">
      {/* Page header */}
      <div className="space-y-1">
        <h1 className="text-[28px] font-normal text-[#202124] tracking-tight">
          Advisory Workspace
        </h1>
        <p className="text-sm text-[#5f6368]">
          Generate &amp; review customer advice packs
        </p>
      </div>

      {/* Search section */}
      <div className="md-card p-5 space-y-4 shadow-md-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-[#1a73e8] text-[20px]">
            tips_and_updates
          </span>
          <h2 className="text-sm font-medium text-[#202124]">
            Generate Advice Draft
          </h2>
        </div>
        <p className="text-sm text-[#5f6368]">
          Enter a customer ID to generate a personalised advice pack:
        </p>
        <div className="flex gap-3">
          <input
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="e.g. C-ASHA001"
            className="md-input flex-1"
            onKeyDown={(e) => e.key === "Enter" && setLoadId(customerId)}
          />
          <button
            onClick={() => setLoadId(customerId)}
            className="btn-filled"
          >
            Generate Draft
          </button>
        </div>
      </div>

      {loadId && <AdviceDraftPanel customerId={loadId} />}
    </div>
  );
}

function AdviceDraftPanel({ customerId }: { customerId: string }) {
  const queryClient = useQueryClient();
  const [edits, setEdits] = useState("");
  const [showEditBox, setShowEditBox] = useState(false);

  const { data: draft, isLoading, isError } = useQuery<AdviceDraft>({
    queryKey: ["advice-draft", customerId],
    queryFn: () => getAdviceDraft(customerId, "advisor-001"),
  });

  const mutation = useMutation({
    mutationFn: () =>
      approveAdviceDraft(draft!.draft_id, "advisor-001", edits || undefined),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["advice-draft", customerId] }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 py-6 text-[#5f6368] text-sm animate-fade-in">
        <span className="material-symbols-outlined text-[#1a73e8] animate-spin text-[20px]">
          progress_activity
        </span>
        Generating advice draft…
      </div>
    );
  }

  if (isError || !draft) {
    return (
      <div
        className="md-card p-4 flex items-start gap-3 border border-[#f5c6c5] bg-[#fce8e6] animate-fade-in"
        role="alert"
      >
        <span className="material-symbols-outlined text-[#c5221f] text-[20px] mt-0.5">
          error
        </span>
        <p className="text-sm text-[#c5221f]">
          Customer not found. Seed customers first using{" "}
          <code className="bg-white/60 px-1 rounded font-mono text-xs">
            ./scripts/seed.sh
          </code>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Draft header */}
      <div className="md-card p-4 flex items-center justify-between shadow-md-1">
        <div className="space-y-0.5">
          <p className="text-sm font-medium text-[#202124]">
            Draft:{" "}
            <span className="font-mono text-[#1a73e8]">{draft.draft_id}</span>
          </p>
          <p className="text-xs text-[#5f6368]">Customer: {draft.customer_id}</p>
        </div>
        <StatusBadge status={draft.status} />
      </div>

      {/* Cross-sell suppression warning */}
      {draft.suppress_cross_sell && (
        <div
          className="md-card p-4 flex items-start gap-3 border border-[#f9c74f] bg-[#fef7e0]"
          role="alert"
        >
          <span className="material-symbols-outlined text-[#b06000] text-[20px] mt-0.5">
            shopping_cart_off
          </span>
          <div>
            <p className="text-sm font-medium text-[#b06000]">
              Cross-Sell Suppressed
            </p>
            <p className="text-sm text-[#b06000] mt-0.5">
              Customer has elevated churn risk or open service issues. Cross-sell
              is disabled for this advice pack.
            </p>
          </div>
        </div>
      )}

      {/* Sentiment note */}
      {draft.service_sentiment_note && (
        <div className="md-card p-4 border-l-4 border-[#f9ab00] bg-[#fef7e0] flex items-start gap-3">
          <span className="material-symbols-outlined text-[#b06000] text-[20px] mt-0.5">
            sentiment_dissatisfied
          </span>
          <div>
            <p className="text-xs font-semibold text-[#b06000] mb-1 uppercase tracking-wide">
              Sentiment Note
            </p>
            <p className="text-sm text-[#202124]">{draft.service_sentiment_note}</p>
          </div>
        </div>
      )}

      {/* Customer context */}
      <div className="md-card p-5 space-y-3 shadow-md-1">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#1a73e8] text-[20px]">
            person_pin
          </span>
          <h2 className="text-sm font-semibold text-[#202124]">
            Customer Context
          </h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
          <div>
            <p className="text-xs text-[#5f6368] uppercase tracking-wide mb-0.5">
              Summary
            </p>
            <p className="text-sm text-[#202124]">
              {draft.customer_context_summary || "—"}
            </p>
          </div>
          {draft.goals_summary && (
            <div>
              <p className="text-xs text-[#5f6368] uppercase tracking-wide mb-0.5">
                Goals
              </p>
              <p className="text-sm text-[#202124]">{draft.goals_summary}</p>
            </div>
          )}
        </div>
        {(draft.product_gaps?.length ?? 0) > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {draft.product_gaps!.map((g: string) => (
              <span
                key={g}
                className="chip bg-[#e8f0fe] text-[#1a73e8] border-[#c5d8fd]"
              >
                <span className="material-symbols-outlined text-[14px]">
                  add_circle
                </span>
                Gap: {g}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Next best actions */}
      {draft.next_best_actions.length > 0 && (
        <div className="md-card overflow-hidden shadow-md-1">
          <div className="flex items-center gap-2 px-5 py-4 border-b border-[#dadce0]">
            <span className="material-symbols-outlined text-[#1a73e8] text-[20px]">
              bolt
            </span>
            <h2 className="text-sm font-semibold text-[#202124]">
              Next Best Actions
            </h2>
          </div>
          <ol className="divide-y divide-[#dadce0]">
            {draft.next_best_actions.map((nba, i) => (
              <NbaItem key={nba.action_id} nba={nba} index={i} />
            ))}
          </ol>
        </div>
      )}

      {/* Full advice draft */}
      {draft.full_advice_text && (
        <div className="md-card p-5 space-y-3 shadow-md-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#1a73e8] text-[20px]">
              description
            </span>
            <h2 className="text-sm font-semibold text-[#202124]">
              Full Advice Draft
            </h2>
          </div>
          <div
            className="bg-[#f8f9fa] border border-[#dadce0] rounded-lg px-4 py-3 overflow-y-auto"
            style={{ maxHeight: 240 }}
          >
            <p className="text-sm text-[#202124] whitespace-pre-wrap leading-relaxed font-mono">
              {draft.full_advice_text}
            </p>
          </div>
        </div>
      )}

      {/* HITL approval gate */}
      {draft.status === "pending_advisor_review" && (
        <div className="md-card p-5 space-y-4 border-2 border-[#f9ab00] bg-[#fef7e0] shadow-md-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#b06000] text-[22px]">
              warning
            </span>
            <h3 className="text-sm font-semibold text-[#202124]">
              Advisor Approval Required
            </h3>
          </div>
          <p className="text-xs text-[#5f6368]">
            No advice can be delivered to the customer without your explicit
            approval.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => {
                setShowEditBox(false);
                mutation.mutate();
              }}
              disabled={mutation.isPending}
              className="btn-filled"
              style={{
                backgroundColor: "#7b2d8b",
                "--btn-filled-bg": "#7b2d8b",
              } as React.CSSProperties}
            >
              {mutation.isPending && !showEditBox ? (
                <span className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] animate-spin">
                    progress_activity
                  </span>
                  Approving…
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px]">
                    check_circle
                  </span>
                  Approve As-Is
                </span>
              )}
            </button>
            <button
              onClick={() => setShowEditBox(!showEditBox)}
              className="btn-tonal"
            >
              <span className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px]">
                  edit
                </span>
                Edit &amp; Approve
              </span>
            </button>
          </div>

          {/* Edit textarea — slides in */}
          {showEditBox && (
            <div className="space-y-3 animate-slide-up">
              <textarea
                value={edits}
                onChange={(e) => setEdits(e.target.value)}
                rows={4}
                placeholder="Enter your edits or additional notes…"
                className="md-input w-full resize-none"
              />
              <button
                onClick={() => mutation.mutate()}
                disabled={mutation.isPending || !edits}
                className="btn-filled disabled:opacity-50"
              >
                {mutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px] animate-spin">
                      progress_activity
                    </span>
                    Saving…
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px]">
                      save
                    </span>
                    Save Edited Approval
                  </span>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Approved state */}
      {draft.status === "approved" && (
        <div className="md-card p-4 flex items-center gap-3 border border-[#a8d5b5] bg-[#e6f4ea] animate-fade-in">
          <span className="material-symbols-outlined text-[#137333] text-[22px]">
            check_circle
          </span>
          <div>
            <p className="text-sm font-medium text-[#137333]">
              Approved — Ready for Delivery
            </p>
            <p className="text-xs text-[#137333]/80">
              Advice pack approved by advisor with no modifications.
            </p>
          </div>
        </div>
      )}

      {/* Edited + approved state */}
      {draft.status === "edited_and_approved" && (
        <div className="md-card p-4 flex items-center gap-3 border border-[#b39ddb] bg-[#f3e8fd] animate-fade-in">
          <span className="material-symbols-outlined text-[#7b2d8b] text-[22px]">
            edit_note
          </span>
          <div>
            <p className="text-sm font-medium text-[#7b2d8b]">
              Edited &amp; Approved
            </p>
            <p className="text-xs text-[#7b2d8b]/80">
              Advisor's edits have been saved and the pack is ready for delivery.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Next Best Action row ─────────────────────────────────────────────── */

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  savings: { bg: "#e6f4ea", text: "#137333" },
  investment: { bg: "#e8f0fe", text: "#1a73e8" },
  insurance: { bg: "#fce8e6", text: "#c5221f" },
  credit: { bg: "#fef7e0", text: "#b06000" },
  mortgage: { bg: "#f3e8fd", text: "#7b2d8b" },
  default: { bg: "#f1f3f4", text: "#5f6368" },
};

function categoryStyle(category: string) {
  const key = category?.toLowerCase() ?? "default";
  return CATEGORY_COLORS[key] ?? CATEGORY_COLORS.default;
}

function NbaItem({
  nba,
  index,
}: {
  nba: {
    action_id: string;
    category: string;
    title: string;
    rationale: string;
    suggested_script?: string | null;
  };
  index: number;
}) {
  const [open, setOpen] = useState(false);
  const style = categoryStyle(nba.category);

  return (
    <li className="px-5 py-4 space-y-2">
      <div className="flex items-start gap-3">
        {/* Step number */}
        <span className="mt-0.5 flex-shrink-0 w-6 h-6 rounded-full bg-[#e8f0fe] text-[#1a73e8] text-xs font-semibold flex items-center justify-center">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            {/* Category chip */}
            <span
              className="chip"
              style={{ backgroundColor: style.bg, color: style.text, borderColor: "transparent" }}
            >
              {nba.category}
            </span>
            <p className="text-sm font-medium text-[#202124]">{nba.title}</p>
          </div>
          <p className="text-xs text-[#5f6368] leading-relaxed">{nba.rationale}</p>

          {/* Collapsible suggested script */}
          {nba.suggested_script && (
            <div>
              <button
                onClick={() => setOpen((o) => !o)}
                className="flex items-center gap-1 text-xs text-[#1a73e8] hover:underline focus:outline-none"
              >
                <span className="material-symbols-outlined text-[14px]">
                  record_voice_over
                </span>
                {open ? "Hide suggested script" : "Suggested script"}
                <span className="material-symbols-outlined text-[14px]">
                  {open ? "expand_less" : "expand_more"}
                </span>
              </button>
              {open && (
                <div className="mt-2 pl-3 border-l-2 border-[#dadce0] animate-fade-in">
                  <p className="text-xs text-[#5f6368] italic leading-relaxed">
                    "{nba.suggested_script}"
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}
