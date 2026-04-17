import { useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { useAuthStore } from "@/store/auth";

const NAV = [
  {
    to: "/",
    label: "Home",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
      </svg>
    ),
  },
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
      </svg>
    ),
  },
  {
    to: "/fraud",
    label: "Fraud",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-1 14H9V9h2v6zm4 0h-2V9h2v6z"/>
      </svg>
    ),
  },
  {
    to: "/loans",
    label: "Loans",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 3c1.93 0 3.5 1.57 3.5 3.5S13.93 13 12 13s-3.5-1.57-3.5-3.5S10.07 6 12 6zm7 13H5v-.23c0-.62.28-1.2.76-1.58C7.47 15.82 9.64 15 12 15s4.53.82 6.24 2.19c.48.38.76.97.76 1.58V19z"/>
      </svg>
    ),
  },
  {
    to: "/advisory",
    label: "Advisory",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
      </svg>
    ),
  },
  {
    to: "/branches",
    label: "Branches",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z"/>
      </svg>
    ),
  },
  {
    to: "/chat",
    label: "Ask AI",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
      </svg>
    ),
    highlight: true,
  },
  {
    to: "/audit",
    label: "Audit",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zM8 15.01l1.41 1.41L11 14.84V19h2v-4.16l1.59 1.59L16 15.01 12.01 11z"/>
      </svg>
    ),
  },
];

export default function Layout() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { userId, roles, logout } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);

  const initials = userId
    ? userId.slice(0, 2).toUpperCase()
    : "??";

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: "#f1f3f4" }}>
      {/* ── Top App Bar ──────────────────────────────────────────────────── */}
      <header
        className="flex items-center h-14 px-4 gap-3 z-30 flex-shrink-0"
        style={{ background: "white", boxShadow: "0 1px 0 #dadce0" }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 mr-4">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold"
            style={{ background: "linear-gradient(135deg, #1a73e8 0%, #34a853 100%)" }}
          >
            FA
          </div>
          <span className="font-display font-medium text-[#202124] text-sm hidden sm:block">
            FinTech Agentic
          </span>
        </div>

        {/* Search bar (decorative / routes to chat) */}
        <button
          onClick={() => navigate("/chat")}
          className="flex-1 max-w-xl flex items-center gap-3 px-4 py-2 rounded-full text-sm text-[#5f6368] transition-all"
          style={{ background: "#f1f3f4", border: "1px solid #f1f3f4" }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.border = "1px solid #dadce0";
            (e.currentTarget as HTMLElement).style.background = "white";
            (e.currentTarget as HTMLElement).style.boxShadow = "0 1px 3px rgba(60,64,67,.3)";
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.border = "1px solid #f1f3f4";
            (e.currentTarget as HTMLElement).style.background = "#f1f3f4";
            (e.currentTarget as HTMLElement).style.boxShadow = "none";
          }}
        >
          <svg viewBox="0 0 24 24" fill="#5f6368" className="w-4 h-4 flex-shrink-0">
            <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
          </svg>
          <span className="text-sm">Ask the banking AI…</span>
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full" style={{ background: "#e8f0fe", color: "#1a73e8" }}>AI</span>
        </button>

        {/* Right actions */}
        <div className="flex items-center gap-1 ml-2">
          {/* Notifications */}
          <button className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-gray-100 relative">
            <svg viewBox="0 0 24 24" fill="#5f6368" className="w-5 h-5">
              <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
            </svg>
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
          </button>

          {/* Avatar */}
          <div className="relative">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-medium ml-1"
              style={{ background: "#1a73e8" }}
            >
              {initials}
            </button>
            {menuOpen && (
              <div
                className="absolute right-0 top-10 w-56 rounded-2xl py-2 z-50 animate-fade-in"
                style={{ background: "white", boxShadow: "0 4px 16px rgba(60,64,67,.3)" }}
              >
                <div className="px-4 py-2 border-b border-[#f1f3f4]">
                  <p className="text-sm font-medium text-[#202124]">{userId}</p>
                  <p className="text-xs text-[#5f6368]">{roles.join(", ")}</p>
                </div>
                <button
                  onClick={() => { logout(); navigate("/login"); setMenuOpen(false); }}
                  className="w-full text-left px-4 py-2.5 text-sm text-[#ea4335] hover:bg-[#fce8e6] transition-colors"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ── Navigation Rail ────────────────────────────────────────────── */}
        <nav
          className="flex flex-col items-center py-3 gap-1 flex-shrink-0 w-[72px] overflow-y-auto"
          style={{ background: "white", borderRight: "1px solid #dadce0" }}
        >
          {NAV.map((item) => {
            const active =
              item.to === "/"
                ? pathname === "/"
                : pathname.startsWith(item.to);

            return (
              <Link
                key={item.to}
                to={item.to}
                className={clsx("nav-item w-14", { active })}
                title={item.label}
              >
                <span
                  className={clsx(
                    "nav-icon w-12 h-8 rounded-2xl flex items-center justify-center transition-colors",
                    active
                      ? "bg-[#e8f0fe] text-[#1a73e8]"
                      : item.highlight
                        ? "text-[#34a853]"
                        : "text-[#5f6368]"
                  )}
                >
                  {item.icon}
                </span>
                <span
                  className={clsx(
                    "text-[10px] leading-tight font-medium",
                    active
                      ? "text-[#1a73e8]"
                      : item.highlight
                        ? "text-[#34a853]"
                        : "text-[#5f6368]"
                  )}
                >
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>

        {/* ── Page content ───────────────────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
