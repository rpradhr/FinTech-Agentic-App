import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAuditTrail, getOpenCases } from "@/services/api";
import StatusBadge from "@/components/StatusBadge";
import type { AuditEvent, Case } from "@/types";
import { format } from "date-fns";

// ── Actor type tag ─────────────────────────────────────────────────────────────
function ActorChip({ type }: { type: string }) {
  if (type === "human") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium
        px-2 py-0.5 rounded-full bg-[#e8f0fe] text-[#1a73e8]">
        <span className="material-symbols-outlined text-[12px]">person</span>
        Human
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-medium
      px-2 py-0.5 rounded-full bg-[#f3e8fd] text-[#7b2d8b]">
      <span className="material-symbols-outlined text-[12px]">smart_toy</span>
      Agent
    </span>
  );
}

// ── Single audit timeline event ────────────────────────────────────────────────
function TimelineEvent({
  event,
  isLast,
}: {
  event: AuditEvent;
  isLast: boolean;
}) {
  const isHuman = event.actor_type === "human";

  return (
    <div className="flex gap-4 px-5 py-4">
      {/* Timeline spine */}
      <div className="flex flex-col items-center flex-shrink-0">
        <div
          className={`w-3 h-3 rounded-full mt-1 ring-2 ring-white shadow-sm ${
            isHuman ? "bg-[#1a73e8]" : "bg-[#7b2d8b]"
          }`}
        />
        {!isLast && (
          <div className="w-px flex-1 bg-[#e0e0e0] mt-1.5" />
        )}
      </div>

      {/* Event content */}
      <div className="flex-1 pb-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <span className="font-mono text-[11px] text-[#9aa0a6]">
            {format(new Date(event.ts), "MMM d, HH:mm:ss")}
          </span>
          <ActorChip type={event.actor_type} />
          <span className="text-[11px] font-medium text-[#5f6368]">
            {event.actor_id}
          </span>
        </div>

        <p className="text-sm font-semibold text-[#202124] capitalize">
          {event.action.replace(/_/g, " ")}
        </p>

        {event.notes && (
          <p className="text-xs text-[#5f6368] mt-1 italic leading-relaxed">
            "{event.notes}"
          </p>
        )}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function AuditConsole() {
  const [objectId, setObjectId] = useState("");
  const [searchId, setSearchId] = useState("");

  const { data: cases = [] } = useQuery<Case[]>({
    queryKey: ["open-cases"],
    queryFn: () => getOpenCases(),
  });

  const { data: trail = [], isLoading } = useQuery<AuditEvent[]>({
    queryKey: ["audit-trail", searchId],
    queryFn: () => getAuditTrail(searchId),
    enabled: !!searchId,
  });

  const handleSearch = () => {
    if (objectId.trim()) setSearchId(objectId.trim());
  };

  return (
    <div className="p-6 space-y-8 max-w-5xl mx-auto animate-fade-in">

      {/* ── Page header ────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-normal text-[#202124]">Audit &amp; Trace Console</h1>
        <p className="text-sm text-[#5f6368] mt-0.5">
          Full immutable event log for every agent and human decision
        </p>
      </div>

      {/* ── Lookup card ────────────────────────────────────────────── */}
      <section className="md-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-[#1a73e8] text-[20px]">
            manage_search
          </span>
          <h2 className="text-sm font-semibold text-[#202124]">
            Reconstruct Audit Trail
          </h2>
        </div>

        <p className="text-xs text-[#5f6368] mb-3">
          Enter any object ID — fraud alert, loan review, advice draft, or case.
        </p>

        <div className="flex gap-2">
          <div className="flex-1 relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2
              text-[18px] text-[#9aa0a6]">
              tag
            </span>
            <input
              value={objectId}
              onChange={(e) => setObjectId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="e.g. FRAUD-001, REV-001, ADV-001, CASE-001"
              className="w-full pl-9 pr-3 py-2.5 border border-[#dadce0] rounded-xl
                text-sm text-[#202124] placeholder-[#9aa0a6]
                focus:outline-none focus:ring-2 focus:ring-[#1a73e8] focus:border-transparent
                transition-all duration-150"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={!objectId.trim()}
            className="btn-filled flex items-center gap-2 disabled:opacity-50
              disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-[18px]">search</span>
            Load Trail
          </button>
        </div>

        {/* Quick-load chips from open cases */}
        {cases.length > 0 && (
          <div className="flex gap-2 flex-wrap mt-3">
            <span className="text-[11px] text-[#9aa0a6] self-center">Quick load:</span>
            {cases.slice(0, 6).map((c) => (
              <button
                key={c.case_id}
                onClick={() => { setObjectId(c.case_id); setSearchId(c.case_id); }}
                className="chip text-[11px] hover:bg-[#e8f0fe] hover:text-[#1a73e8]
                  hover:border-[#1a73e8] transition-colors font-mono"
              >
                {c.case_id}
              </button>
            ))}
          </div>
        )}
      </section>

      {/* ── Audit timeline ─────────────────────────────────────────── */}
      {searchId && (
        <section className="md-card overflow-hidden animate-slide-up">
          <div className="px-5 py-4 border-b border-[#e0e0e0] flex items-center
            justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[#1a73e8] text-[20px]">
                history
              </span>
              <h2 className="text-sm font-semibold text-[#202124]">
                Trail: <span className="font-mono text-[#1a73e8]">{searchId}</span>
              </h2>
            </div>
            {trail.length > 0 && (
              <span className="chip text-[11px]">
                {trail.length} event{trail.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          {isLoading ? (
            <div className="px-5 py-8 flex items-center gap-3 justify-center">
              <span className="material-symbols-outlined text-[#1a73e8] animate-spin text-[24px]">
                progress_activity
              </span>
              <span className="text-sm text-[#5f6368]">Loading audit trail…</span>
            </div>
          ) : trail.length === 0 ? (
            <div className="px-5 py-12 text-center">
              <span className="material-symbols-outlined text-[48px] text-[#dadce0]">
                find_in_page
              </span>
              <p className="text-sm text-[#9aa0a6] mt-2">
                No audit events found for <span className="font-mono">{searchId}</span>
              </p>
              <p className="text-xs text-[#9aa0a6] mt-1">
                Ensure the object exists and has been processed by an agent.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[#f1f3f4]">
              {trail.map((event, i) => (
                <TimelineEvent
                  key={event.event_id}
                  event={event}
                  isLast={i === trail.length - 1}
                />
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Open cases ─────────────────────────────────────────────── */}
      <section className="md-card overflow-hidden">
        <div className="px-5 py-4 border-b border-[#e0e0e0] flex items-center
          justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#1a73e8] text-[20px]">
              folder_open
            </span>
            <h2 className="text-sm font-semibold text-[#202124]">Open Cases</h2>
          </div>
          {cases.length > 0 && (
            <span className="chip text-[11px]">{cases.length} open</span>
          )}
        </div>

        {cases.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <span className="material-symbols-outlined text-[48px] text-[#dadce0]">
              inbox
            </span>
            <p className="text-sm text-[#9aa0a6] mt-2">No open cases at this time.</p>
          </div>
        ) : (
          <div className="divide-y divide-[#f1f3f4]">
            {cases.map((c) => (
              <div
                key={c.case_id}
                className="flex items-center gap-3 px-5 py-3.5
                  hover:bg-[#f8f9fa] transition-colors group"
              >
                <button
                  onClick={() => { setObjectId(c.case_id); setSearchId(c.case_id); }}
                  className="font-mono text-xs text-[#1a73e8] hover:underline
                    flex-shrink-0 flex items-center gap-1"
                  title="Load audit trail"
                >
                  <span className="material-symbols-outlined text-[14px]">
                    open_in_new
                  </span>
                  {c.case_id}
                </button>

                <span className="text-[10px] bg-[#e8f0fe] text-[#1a73e8] px-2
                  py-0.5 rounded-full font-medium uppercase tracking-wide flex-shrink-0">
                  {c.case_type}
                </span>

                <p className="flex-1 text-sm text-[#202124] truncate min-w-0">
                  {c.title}
                </p>

                <StatusBadge status={c.status} />
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Legend ──────────────────────────────────────────────────── */}
      <div className="flex items-center gap-6 px-2">
        <p className="text-xs text-[#9aa0a6]">Event types:</p>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-[#1a73e8] ring-2 ring-white shadow-sm" />
          <span className="text-xs text-[#5f6368]">Human decision</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-[#7b2d8b] ring-2 ring-white shadow-sm" />
          <span className="text-xs text-[#5f6368]">Agent action</span>
        </div>
        <p className="text-xs text-[#9aa0a6] ml-auto">
          Audit log is append-only and immutable.
        </p>
      </div>
    </div>
  );
}
