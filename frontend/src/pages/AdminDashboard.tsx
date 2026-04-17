import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from "recharts";
import {
  fraudTrend, sentimentDist, loanFunnel, branchRadar,
  agentActivity, kpiCards, churnTrend, modelPerf,
} from "@/data/mockMetrics";

// ── Small helpers ─────────────────────────────────────────────────────────────
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-base font-display font-medium text-[#202124] mb-3">
      {children}
    </h2>
  );
}

function ChartCard({
  title, subtitle, children, className = "",
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`md-card p-5 ${className}`}>
      <div className="mb-4">
        <p className="text-sm font-display font-medium text-[#202124]">{title}</p>
        {subtitle && <p className="text-xs text-[#5f6368] mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

// ── KPI Icon SVGs ─────────────────────────────────────────────────────────────
const ICONS: Record<string, React.ReactNode> = {
  shield: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
    </svg>
  ),
  speed: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M20.38 8.57l-1.23 1.85a8 8 0 0 1-.22 7.58H5.07A8 8 0 0 1 15.58 6.85l1.85-1.23A10 10 0 0 0 3.35 19a2 2 0 0 0 1.72 1h13.85a2 2 0 0 0 1.74-1 10 10 0 0 0-.27-10.43zM10.59 15.41a2 2 0 0 0 2.83 0l5.66-8.49-8.49 5.66a2 2 0 0 0 0 2.83z"/>
    </svg>
  ),
  trending_down: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M16 18l2.29-2.29-4.88-4.88-4 4L2 7.41 3.41 6l6 6 4-4 6.3 6.29L22 12v6z"/>
    </svg>
  ),
  feedback: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 12h-2v-2h2v2zm0-4h-2V6h2v4z"/>
    </svg>
  ),
  person_off: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M20 17.17l-3.37-3.38c.91-.46 1.74-1.08 2.43-1.84L20 13v4.17zm.49 4.24l-1.73-1.73A5.998 5.998 0 0 1 15 21H9c-1.66 0-3-.34-3-1v-1c0-2.28 2.5-4.25 6-4.72L2.1 4.4 3.51 3 21.9 21.4l-1.41 1.01zM12 5c-2.21 0-4 1.79-4 4 0 .47.08.92.22 1.35L13.8 15.9c-.6.07-1.2.1-1.8.1-3.86 0-7 1.92-7 4v1h10.17l-4-4H12c2.21 0 4-1.79 4-4s-1.79-4-4-4z"/>
    </svg>
  ),
  thumb_up: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/>
    </svg>
  ),
};

// ── Custom tooltip ────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-xl px-3 py-2 text-xs"
      style={{ background: "white", boxShadow: "0 4px 12px rgba(60,64,67,.2)", border: "1px solid #dadce0" }}
    >
      <p className="font-medium text-[#202124] mb-1">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-[#5f6368]">{p.name}:</span>
          <span className="font-medium text-[#202124]">{p.value}</span>
        </div>
      ))}
    </div>
  );
};

// ── Main dashboard ────────────────────────────────────────────────────────────
export default function AdminDashboard() {
  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-medium text-[#202124]">
            Platform Dashboard
          </h1>
          <p className="text-sm text-[#5f6368] mt-0.5">
            Live agent performance · 14-day window · Auto-refreshes every 30s
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-outlined text-xs">Export PDF</button>
          <button className="btn-tonal text-xs">Configure Alerts</button>
        </div>
      </div>

      {/* ── KPI row ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {kpiCards.map((card) => (
          <div
            key={card.label}
            className="md-card p-4 flex flex-col gap-2 hover:translate-y-[-2px] transition-transform cursor-default"
          >
            <div className="flex items-center justify-between">
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center"
                style={{ background: `${card.color}18`, color: card.color }}
              >
                {ICONS[card.icon]}
              </div>
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{
                  background: card.positive ? "#e6f4ea" : "#fce8e6",
                  color:      card.positive ? "#137333" : "#c5221f",
                }}
              >
                {card.delta}
              </span>
            </div>
            <div>
              <p className="text-2xl font-display font-medium text-[#202124] leading-tight">
                {card.value}
              </p>
              <p className="text-[11px] text-[#5f6368] mt-0.5 leading-tight">
                {card.label}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Row 2: Fraud trend + Sentiment pie ─────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <ChartCard
          title="Fraud Alert Trend"
          subtitle="14-day volume by severity"
          className="xl:col-span-2"
        >
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={fraudTrend} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                {[
                  { id: "critical", color: "#c5221f" },
                  { id: "high",     color: "#ea4335" },
                  { id: "medium",   color: "#fbbc04" },
                  { id: "cleared",  color: "#34a853" },
                ].map(({ id, color }) => (
                  <linearGradient key={id} id={`g-${id}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={color} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f3f4" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#5f6368" }} axisLine={false} tickLine={false} interval={2} />
              <YAxis tick={{ fontSize: 10, fill: "#5f6368" }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              {[
                { key: "critical", color: "#c5221f" },
                { key: "high",     color: "#ea4335" },
                { key: "medium",   color: "#fbbc04" },
                { key: "cleared",  color: "#34a853" },
              ].map(({ key, color }) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={color}
                  strokeWidth={2}
                  fill={`url(#g-${key})`}
                  dot={false}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Customer Sentiment" subtitle="Distribution across all interactions">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={sentimentDist}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
              >
                {sentimentDist.map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip
                formatter={(v: any, n: any) => [`${v}%`, n]}
                contentStyle={{ borderRadius: 12, border: "1px solid #dadce0", fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 space-y-1">
            {sentimentDist.map((s) => (
              <div key={s.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                  <span className="text-[#5f6368]">{s.name}</span>
                </div>
                <span className="font-medium text-[#202124]">{s.value}%</span>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>

      {/* ── Row 3: Agent activity + Loan funnel ───────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <ChartCard
          title="Agent Activity"
          subtitle="Requests processed per agent (last 7 days)"
          className="xl:col-span-2"
        >
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={agentActivity} margin={{ top: 4, right: 4, bottom: 0, left: -20 }} barSize={10}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f3f4" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#5f6368" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#5f6368" }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="fraud"     name="Fraud"     fill="#ea4335" radius={[3,3,0,0]} />
              <Bar dataKey="sentiment" name="Sentiment" fill="#1a73e8" radius={[3,3,0,0]} />
              <Bar dataKey="loan"      name="Loan"      fill="#34a853" radius={[3,3,0,0]} />
              <Bar dataKey="branch"    name="Branch"    fill="#fbbc04" radius={[3,3,0,0]} />
              <Bar dataKey="advisory"  name="Advisory"  fill="#9c27b0" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Loan Review Funnel" subtitle="Current pipeline stage counts">
          <div className="space-y-3 pt-1">
            {loanFunnel.map((item, i) => (
              <div key={item.stage}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-[#5f6368]">{item.stage}</span>
                  <span className="text-xs font-medium text-[#202124]">{item.count}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-[#f1f3f4] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${(item.count / loanFunnel[0].count) * 100}%`,
                      background: item.fill,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>

      {/* ── Row 4: Branch radar + Churn risk + Model perf ─────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <ChartCard title="Branch Performance Radar" subtitle="Multi-metric comparison">
          <ResponsiveContainer width="100%" height={240}>
            <RadarChart data={branchRadar} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
              <PolarGrid stroke="#e8eaed" />
              <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10, fill: "#5f6368" }} />
              <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9, fill: "#9aa0a6" }} />
              <Radar name="West Side" dataKey="West Side" stroke="#1a73e8" fill="#1a73e8" fillOpacity={0.15} />
              <Radar name="Downtown"  dataKey="Downtown"  stroke="#34a853" fill="#34a853" fillOpacity={0.12} />
              <Radar name="East Park" dataKey="East Park" stroke="#ea4335" fill="#ea4335" fillOpacity={0.1} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
            </RadarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Churn Risk Trend" subtitle="Customers at risk over 14 days">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={churnTrend} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f3f4" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#5f6368" }} axisLine={false} tickLine={false} interval={3} />
              <YAxis tick={{ fontSize: 10, fill: "#5f6368" }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="high"   name="High Risk"   stroke="#ea4335" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="medium" name="Medium Risk" stroke="#fbbc04" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="low"    name="Low Risk"    stroke="#34a853" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Agent Model Performance" subtitle="Precision, recall, F1 by agent">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[#e8eaed]">
                  {["Agent", "Prec.", "Recall", "F1", "Lat."].map((h) => (
                    <th key={h} className="py-2 pr-3 text-left font-medium text-[#5f6368]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {modelPerf.map((row) => (
                  <tr key={row.agent} className="border-b border-[#f1f3f4]">
                    <td className="py-2.5 pr-3 font-medium text-[#202124]">{row.agent}</td>
                    <td className="py-2.5 pr-3">
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1.5 rounded-full bg-[#f1f3f4] overflow-hidden">
                          <div className="h-full rounded-full bg-[#1a73e8]" style={{ width: `${row.precision}%` }} />
                        </div>
                        <span className="text-[#202124]">{row.precision}%</span>
                      </div>
                    </td>
                    <td className="py-2.5 pr-3">
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1.5 rounded-full bg-[#f1f3f4] overflow-hidden">
                          <div className="h-full rounded-full bg-[#34a853]" style={{ width: `${row.recall}%` }} />
                        </div>
                        <span className="text-[#202124]">{row.recall}%</span>
                      </div>
                    </td>
                    <td className="py-2.5 pr-3">
                      <span
                        className="font-medium"
                        style={{ color: row.f1 >= 85 ? "#137333" : row.f1 >= 75 ? "#b06000" : "#c5221f" }}
                      >
                        {row.f1}%
                      </span>
                    </td>
                    <td className="py-2.5 text-[#5f6368]">{row.latency}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
