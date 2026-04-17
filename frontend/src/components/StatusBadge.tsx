import clsx from "clsx";

const map: Record<string, string> = {
  open:                   "bg-[#e8f0fe] text-[#1a73e8]",
  pending_analyst_review: "bg-[#fef7e0] text-[#b06000]",
  pending_advisor_review: "bg-[#fef7e0] text-[#b06000]",
  pending_documents:      "bg-[#fef7e0] text-[#b06000]",
  under_review:           "bg-[#e8f0fe] text-[#1a73e8]",
  confirmed_fraud:        "bg-[#fce8e6] text-[#c5221f]",
  declined:               "bg-[#fce8e6] text-[#c5221f]",
  cleared:                "bg-[#e6f4ea] text-[#137333]",
  approved:               "bg-[#e6f4ea] text-[#137333]",
  conditionally_approved: "bg-[#e6f4ea] text-[#1e8e3e]",
  edited_and_approved:    "bg-[#e6f4ea] text-[#1e8e3e]",
  escalated:              "bg-[#fce8e6] text-[#c5221f]",
  delivered:              "bg-[#e8d5f5] text-[#7b2d8b]",
  draft:                  "bg-[#f1f3f4] text-[#5f6368]",
  closed:                 "bg-[#f1f3f4] text-[#5f6368]",
  submitted:              "bg-[#e8f0fe] text-[#1a73e8]",
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = map[status] ?? "bg-[#f1f3f4] text-[#5f6368]";
  return (
    <span className={clsx("status-pill", cls)}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
