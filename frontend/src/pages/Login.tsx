import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { devLogin } from "@/services/api";
import { useAuthStore } from "@/store/auth";

const DEMO_ROLES = [
  {
    label: "Fraud Analyst",
    description: "Review & action fraud alerts",
    roles: ["fraud_analyst", "compliance_reviewer"],
    icon: "security",
    color: "#c5221f",
    bg: "#fce8e6",
  },
  {
    label: "Underwriter",
    description: "Evaluate loan applications",
    roles: ["underwriter", "compliance_reviewer"],
    icon: "account_balance",
    color: "#1a73e8",
    bg: "#e8f0fe",
  },
  {
    label: "Financial Advisor",
    description: "Generate & deliver client advice",
    roles: ["financial_advisor"],
    icon: "tips_and_updates",
    color: "#7b2d8b",
    bg: "#f3e8fd",
  },
  {
    label: "Branch Manager",
    description: "Monitor branch operations",
    roles: ["branch_manager"],
    icon: "storefront",
    color: "#137333",
    bg: "#e6f4ea",
  },
  {
    label: "Admin",
    description: "Full platform access",
    roles: ["admin"],
    icon: "admin_panel_settings",
    color: "#5f6368",
    bg: "#f1f3f4",
  },
];

export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [loading, setLoading] = useState(false);
  const [loadingRole, setLoadingRole] = useState<string | null>(null);
  const [error, setError] = useState("");

  const login = async (userId: string, roles: string[], label: string) => {
    setLoading(true);
    setLoadingRole(label);
    setError("");
    try {
      const data = await devLogin(userId, roles);
      setAuth(data.access_token, userId, roles);
      navigate("/");
    } catch {
      setError("Login failed — is the backend running?");
    } finally {
      setLoading(false);
      setLoadingRole(null);
    }
  };

  return (
    <div className="min-h-screen flex" style={{ background: "#f8f9fa" }}>
      {/* ── Left panel (branding) ──────────────────────────────────────── */}
      <div
        className="hidden lg:flex flex-col justify-between w-[420px] flex-shrink-0 p-10"
        style={{
          background: "linear-gradient(160deg, #0d47a1 0%, #1a73e8 60%, #4285f4 100%)",
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur-sm">
            <span className="material-symbols-outlined text-white text-[22px]">
              account_tree
            </span>
          </div>
          <span className="text-white font-semibold text-lg tracking-tight">
            FinTech Agentic
          </span>
        </div>

        {/* Hero text */}
        <div className="space-y-6">
          <h1 className="text-white text-4xl font-light leading-tight">
            AI-powered<br />
            <span className="font-semibold">banking operations</span>
          </h1>
          <p className="text-blue-100 text-sm leading-relaxed max-w-xs">
            Five specialized agents — fraud detection, sentiment analysis, loan review,
            branch monitoring, and financial advisory — orchestrated by a supervisor agent.
          </p>

          {/* Feature list */}
          <ul className="space-y-3">
            {[
              { icon: "security",        text: "Real-time fraud detection" },
              { icon: "psychology",      text: "Customer sentiment analysis" },
              { icon: "verified_user",   text: "Human-in-the-loop approvals" },
              { icon: "monitoring",      text: "Full audit trail" },
            ].map((f) => (
              <li key={f.text} className="flex items-center gap-3 text-sm text-blue-100">
                <span
                  className="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center flex-shrink-0"
                >
                  <span className="material-symbols-outlined text-white text-[16px]">
                    {f.icon}
                  </span>
                </span>
                {f.text}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-blue-200 text-xs">
          © 2026 FinTech Agentic Platform · Demo Environment
        </p>
      </div>

      {/* ── Right panel (login) ────────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md animate-fade-in">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: "#1a73e8" }}
            >
              <span className="material-symbols-outlined text-white text-[22px]">
                account_tree
              </span>
            </div>
            <span className="font-semibold text-[#202124] text-lg">
              FinTech Agentic
            </span>
          </div>

          <div className="md-card p-8 shadow-md-2">
            <h2 className="text-2xl font-normal text-[#202124] mb-1">
              Welcome back
            </h2>
            <p className="text-sm text-[#5f6368] mb-8">
              Select a role to enter the platform
            </p>

            <div className="space-y-3">
              {DEMO_ROLES.map((r) => (
                <button
                  key={r.label}
                  onClick={() =>
                    login(
                      r.label.toLowerCase().replace(/ /g, "_"),
                      r.roles,
                      r.label
                    )
                  }
                  disabled={loading}
                  className="w-full flex items-center gap-4 px-4 py-3.5 rounded-xl border
                    border-[#dadce0] hover:border-[#1a73e8] hover:shadow-md-1
                    transition-all duration-150 text-left group
                    disabled:opacity-60 disabled:cursor-not-allowed
                    bg-white hover:bg-[#f8fbff]"
                >
                  {/* Role icon */}
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center
                      flex-shrink-0 transition-transform duration-150 group-hover:scale-110"
                    style={{ background: r.bg }}
                  >
                    {loadingRole === r.label ? (
                      <span
                        className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin"
                        style={{ borderColor: r.color }}
                      />
                    ) : (
                      <span
                        className="material-symbols-outlined text-[20px]"
                        style={{ color: r.color }}
                      >
                        {r.icon}
                      </span>
                    )}
                  </div>

                  {/* Labels */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#202124] group-hover:text-[#1a73e8]
                      transition-colors">
                      {r.label}
                    </p>
                    <p className="text-xs text-[#9aa0a6]">{r.description}</p>
                  </div>

                  <span
                    className="material-symbols-outlined text-[20px] text-[#dadce0]
                      group-hover:text-[#1a73e8] transition-colors"
                  >
                    chevron_right
                  </span>
                </button>
              ))}
            </div>

            {error && (
              <div className="mt-4 flex items-center gap-2 p-3 rounded-lg bg-[#fce8e6] text-[#c5221f]">
                <span className="material-symbols-outlined text-[18px]">error</span>
                <p className="text-sm">{error}</p>
              </div>
            )}

            <div className="mt-6 flex items-center gap-2 p-3 rounded-lg bg-[#fef7e0]">
              <span className="material-symbols-outlined text-[#b06000] text-[18px]">info</span>
              <p className="text-xs text-[#b06000]">
                Development login — In production, use your organization's SSO provider.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
