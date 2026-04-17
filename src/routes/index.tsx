import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { endpoints, apiBaseUrl } from "@/lib/api";
import { Surface, PageHeader, Chip, M3Button } from "@/components/m3";
import {
  ShieldAlert,
  Landmark,
  HeartHandshake,
  Building2,
  MessageSquareHeart,
  ArrowUpRight,
  Activity,
  Users,
  CheckCircle2,
} from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Overview — FinTech Agentic" },
      {
        name: "description",
        content: "Operational overview across fraud, loans, advisory, branches, and sentiment.",
      },
    ],
  }),
  component: OverviewPage,
});

const AGENTS = [
  {
    to: "/fraud",
    title: "Fraud Detection",
    desc: "Real-time transaction scoring with HITL approval.",
    icon: ShieldAlert,
    accent: "text-destructive",
    bg: "bg-destructive/10",
  },
  {
    to: "/loans",
    title: "Loan Review",
    desc: "Underwriting checks: DTI, LTV, completeness.",
    icon: Landmark,
    accent: "text-info",
    bg: "bg-info/10",
  },
  {
    to: "/advisory",
    title: "Financial Advisory",
    desc: "Next-best-action drafts for advisor review.",
    icon: HeartHandshake,
    accent: "text-primary",
    bg: "bg-primary/12",
  },
  {
    to: "/branches",
    title: "Branch Monitoring",
    desc: "KPI ranking & operational recommendations.",
    icon: Building2,
    accent: "text-success",
    bg: "bg-success/10",
  },
  {
    to: "/sentiment",
    title: "Sentiment Analysis",
    desc: "Customer signal classification & risk scoring.",
    icon: MessageSquareHeart,
    accent: "text-warning-foreground",
    bg: "bg-warning/20",
  },
] as const;

function OverviewPage() {
  const health = useQuery({ queryKey: ["health"], queryFn: endpoints.health, retry: 0 });
  const cases = useQuery({
    queryKey: ["cases", "open"],
    queryFn: () => endpoints.listCases(),
    retry: 0,
  });
  const fraud = useQuery({
    queryKey: ["fraud", "alerts"],
    queryFn: endpoints.listFraudAlerts,
    retry: 0,
  });

  const stats = [
    {
      label: "Backend",
      value: health.data?.status ?? (health.isError ? "offline" : "—"),
      sub: health.data?.env ?? apiBaseUrl,
      icon: Activity,
      tone: health.isError ? "danger" : "success",
    },
    {
      label: "Open cases",
      value: cases.data?.length ?? (cases.isError ? "—" : "…"),
      sub: "Across all agents",
      icon: Users,
      tone: "info",
    },
    {
      label: "Fraud alerts",
      value: fraud.data?.length ?? (fraud.isError ? "—" : "…"),
      sub: "Pending analyst review",
      icon: ShieldAlert,
      tone: "warning",
    },
    {
      label: "HITL gates",
      value: "5/5",
      sub: "All agents gated",
      icon: CheckCircle2,
      tone: "success",
    },
  ] as const;

  return (
    <div>
      <PageHeader
        eyebrow="Operations Console"
        title="Banking agents at a glance"
        subtitle="Specialist AI agents for fraud, loans, advisory, branches, and sentiment — every consequential action gated by a human reviewer with a full audit trail."
        actions={
          <Link to="/chat">
            <M3Button variant="filled">Open Assistant</M3Button>
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <Surface key={s.label} tone="container" className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <div className="m3-label text-on-surface-variant">{s.label}</div>
                <div className="mt-1 text-3xl font-semibold tracking-tight text-on-surface">
                  {String(s.value)}
                </div>
                <div className="mt-1 text-xs text-on-surface-variant">{s.sub}</div>
              </div>
              <div className="grid h-10 w-10 place-items-center rounded-2xl bg-surface-container-highest text-primary">
                <s.icon className="h-5 w-5" />
              </div>
            </div>
            <div className="mt-3">
              <Chip tone={s.tone}>{s.tone}</Chip>
            </div>
          </Surface>
        ))}
      </div>

      <h2 className="m3-title mt-12 text-on-surface">Agents</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {AGENTS.map((a) => (
          <Link key={a.to} to={a.to} className="group">
            <Surface
              tone="container"
              className="m3-state h-full p-6 transition-shadow hover:m3-elev-2"
            >
              <div className="flex items-center gap-3">
                <div className={`grid h-11 w-11 place-items-center rounded-2xl ${a.bg} ${a.accent}`}>
                  <a.icon className="h-6 w-6" />
                </div>
                <div className="m3-title text-on-surface">{a.title}</div>
                <ArrowUpRight className="ml-auto h-5 w-5 text-on-surface-variant transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </div>
              <p className="mt-3 text-sm text-on-surface-variant">{a.desc}</p>
            </Surface>
          </Link>
        ))}
      </div>
    </div>
  );
}
