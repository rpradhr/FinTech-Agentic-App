import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { getLoanReview, submitLoanDecision } from "@/services/api";
import StatusBadge from "@/components/StatusBadge";

export function LoanReviewList() {
  const [applicationId, setApplicationId] = useState("");
  const [searchId, setSearchId] = useState("");

  return (
    <div className="p-6 space-y-6 max-w-3xl animate-fade-in">
      {/* ── Page header ─────────────────────────────────────────────── */}
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-[#1a73e8] text-3xl">
            rate_review
          </span>
          <h1
            className="text-2xl font-semibold"
            style={{ color: "#202124", fontFamily: "'Google Sans', sans-serif" }}
          >
            Loan Review Workbench
          </h1>
        </div>
        <p className="text-sm pl-12" style={{ color: "#5f6368" }}>
          Retrieve an AI-prepared review pack and record your underwriting decision.
        </p>
      </div>

      {/* ── Search card ─────────────────────────────────────────────── */}
      <div className="md-card p-5 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-base" style={{ color: "#5f6368" }}>
            search
          </span>
          <span className="text-sm font-medium" style={{ color: "#202124" }}>
            Load Review Pack
          </span>
        </div>
        <div className="flex gap-3 items-start">
          <div className="flex-1 space-y-1">
            <input
              value={applicationId}
              onChange={(e) => setApplicationId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && setSearchId(applicationId)}
              placeholder="e.g. L-001"
              className="md-input"
            />
            <p className="text-xs pl-1" style={{ color: "#5f6368" }}>
              Enter the application ID assigned at submission.
            </p>
          </div>
          <button
            onClick={() => setSearchId(applicationId)}
            className="btn-filled shrink-0"
          >
            <span className="material-symbols-outlined text-base">download</span>
            Load Review
          </button>
        </div>
      </div>

      {/* ── Review panel ────────────────────────────────────────────── */}
      {searchId && <LoanReviewPanel applicationId={searchId} />}
    </div>
  );
}

function LoanReviewPanel({ applicationId }: { applicationId: string }) {
  const queryClient = useQueryClient();
  const [decision, setDecision] = useState("approved");
  const [notes, setNotes] = useState("");

  const { data: review, isLoading, isError } = useQuery({
    queryKey: ["loan-review", applicationId],
    queryFn: () => getLoanReview(applicationId),
  });

  const mutation = useMutation({
    mutationFn: () => submitLoanDecision(applicationId, "uw-001", decision, notes),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["loan-review", applicationId] }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 px-2 py-4" style={{ color: "#5f6368" }}>
        <span className="material-symbols-outlined animate-spin text-lg text-[#1a73e8]">
          progress_activity
        </span>
        <span className="text-sm">Loading review…</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div
        className="md-card p-4 flex items-start gap-3"
        style={{ borderLeft: "4px solid #c5221f" }}
      >
        <span className="material-symbols-outlined text-xl mt-0.5" style={{ color: "#c5221f" }}>
          error
        </span>
        <div>
          <p className="text-sm font-medium" style={{ color: "#c5221f" }}>
            Review not found
          </p>
          <p className="text-xs mt-0.5" style={{ color: "#5f6368" }}>
            Submit the application first via the API or seed data.
          </p>
        </div>
      </div>
    );
  }

  if (!review) return null;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* ── Step 1: Review header card ───────────────────────────────── */}
      <div className="md-card p-5 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className="flex items-center justify-center w-6 h-6 rounded-full text-xs font-semibold text-white shrink-0"
              style={{ background: "#1a73e8" }}
            >
              1
            </span>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "#5f6368" }}>
                Review ID
              </p>
              <h2 className="text-base font-semibold" style={{ color: "#202124", fontFamily: "'Google Sans', sans-serif" }}>
                {review.review_id}
              </h2>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {/* Confidence score pill */}
            <span
              className="chip"
              style={{ background: "#e8f0fe", borderColor: "#c5d9f8", color: "#1a73e8" }}
            >
              <span className="material-symbols-outlined text-xs">bar_chart</span>
              {(review.confidence_score * 100).toFixed(0)}% confidence
            </span>
            <StatusBadge status={review.recommended_status} />
          </div>
        </div>
        <div
          className="flex items-center gap-2 pt-1 pb-0.5 text-xs"
          style={{ color: "#5f6368", borderTop: "1px solid #e8eaed" }}
        >
          <span className="material-symbols-outlined text-sm">folder_open</span>
          Application:&nbsp;<span className="font-medium" style={{ color: "#202124" }}>{review.application_id}</span>
        </div>
      </div>

      {/* ── Step 2: Summary blockquote card ─────────────────────────── */}
      <div className="md-card p-5 space-y-3">
        <div className="flex items-center gap-2">
          <span
            className="flex items-center justify-center w-6 h-6 rounded-full text-xs font-semibold text-white shrink-0"
            style={{ background: "#1a73e8" }}
          >
            2
          </span>
          <span className="text-sm font-medium flex items-center gap-1.5" style={{ color: "#202124" }}>
            <span className="material-symbols-outlined text-base text-[#1a73e8]">account_balance</span>
            Summary
          </span>
        </div>
        <blockquote
          className="ml-8 pl-4 py-2 text-sm leading-relaxed italic"
          style={{
            borderLeft: "3px solid #1a73e8",
            background: "#f8f9fa",
            borderRadius: "0 8px 8px 0",
            color: "#202124",
          }}
        >
          {review.summary}
        </blockquote>
      </div>

      {/* ── Step 3: Missing documents (conditional) ──────────────────── */}
      {review.missing_documents.length > 0 && (
        <div
          className="md-card p-5 space-y-3"
          style={{ borderLeft: "4px solid #fbbc04" }}
        >
          <div className="flex items-center gap-2">
            <span
              className="flex items-center justify-center w-6 h-6 rounded-full text-xs font-semibold text-white shrink-0"
              style={{ background: "#b06000" }}
            >
              3
            </span>
            <span
              className="text-sm font-medium flex items-center gap-1.5"
              style={{ color: "#b06000" }}
            >
              <span className="material-symbols-outlined text-base">list_alt</span>
              Missing Documents
            </span>
          </div>
          <ul className="ml-8 space-y-1.5">
            {review.missing_documents.map((d: string) => (
              <li key={d} className="flex items-start gap-2 text-sm" style={{ color: "#b06000" }}>
                <span className="material-symbols-outlined text-base mt-0.5 shrink-0">
                  radio_button_unchecked
                </span>
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Step 4: AI Rationale (conditional) ──────────────────────── */}
      {review.ai_explanation && (
        <div className="md-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <span
              className="flex items-center justify-center w-6 h-6 rounded-full text-xs font-semibold text-white shrink-0"
              style={{ background: "#1a73e8" }}
            >
              {review.missing_documents.length > 0 ? "4" : "3"}
            </span>
            <span className="text-sm font-medium flex items-center gap-1.5" style={{ color: "#202124" }}>
              <span className="material-symbols-outlined text-base text-[#1a73e8]">psychology</span>
              AI Rationale
            </span>
          </div>
          <p className="ml-8 text-sm leading-relaxed italic" style={{ color: "#5f6368" }}>
            {review.ai_explanation}
          </p>
        </div>
      )}

      {/* ── HITL decision gate ───────────────────────────────────────── */}
      {!review.underwriter_decision ? (
        <div
          className="md-card p-5 space-y-4"
          style={{ border: "2px solid #fbbc04", background: "#fef7e0" }}
        >
          {/* Card header */}
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-xl" style={{ color: "#b06000" }}>
              lock
            </span>
            <div>
              <h3
                className="text-sm font-semibold"
                style={{ color: "#202124", fontFamily: "'Google Sans', sans-serif" }}
              >
                Underwriter Decision Required
              </h3>
              <p className="text-xs" style={{ color: "#b06000" }}>
                Your decision will be recorded and trigger the next workflow stage.
              </p>
            </div>
          </div>

          {/* Divider */}
          <div style={{ borderTop: "1px solid #f9e9b0" }} />

          {/* Select */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium" style={{ color: "#5f6368" }}>
              Decision
            </label>
            <select
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              style={{
                width: "100%",
                border: "1px solid #dadce0",
                borderRadius: "8px",
                padding: "10px 14px",
                fontSize: "14px",
                background: "white",
                color: "#202124",
                outline: "none",
                transition: "border-color 0.2s, box-shadow 0.2s",
                appearance: "auto",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = "#1a73e8";
                e.target.style.boxShadow = "0 0 0 2px rgba(26,115,232,0.12)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "#dadce0";
                e.target.style.boxShadow = "none";
              }}
            >
              <option value="approved">Approve</option>
              <option value="conditionally_approved">Conditionally Approve</option>
              <option value="declined">Decline</option>
              <option value="pending_documents">Request Additional Documents</option>
            </select>
          </div>

          {/* Textarea */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium" style={{ color: "#5f6368" }}>
              Notes <span style={{ color: "#9aa0a6" }}>(optional)</span>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Add context or conditions for this decision…"
              className="md-input"
              style={{ resize: "vertical" }}
            />
          </div>

          {/* Submit button */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="btn-filled"
            >
              {mutation.isPending ? (
                <>
                  <span className="material-symbols-outlined text-base animate-spin">
                    progress_activity
                  </span>
                  Submitting…
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-base">task_alt</span>
                  Record Decision
                </>
              )}
            </button>
            {mutation.isError && (
              <span className="text-xs flex items-center gap-1" style={{ color: "#c5221f" }}>
                <span className="material-symbols-outlined text-sm">error</span>
                Submission failed — please retry.
              </span>
            )}
          </div>
        </div>
      ) : (
        /* ── Decision recorded success state ──────────────────────────── */
        <div
          className="md-card p-4 flex items-center gap-3"
          style={{ background: "#e6f4ea", borderLeft: "4px solid #34a853" }}
        >
          <span className="material-symbols-outlined text-xl shrink-0" style={{ color: "#137333" }}>
            check_circle
          </span>
          <div>
            <p className="text-sm font-medium" style={{ color: "#137333" }}>
              Decision recorded
            </p>
            <p className="text-xs mt-0.5" style={{ color: "#137333", opacity: 0.8 }}>
              Outcome:&nbsp;
              <strong className="capitalize">
                {review.underwriter_decision.replace(/_/g, " ")}
              </strong>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
