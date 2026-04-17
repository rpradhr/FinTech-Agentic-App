import { Link, useRouterState } from "@tanstack/react-router";
import {
  ShieldAlert,
  Landmark,
  HeartHandshake,
  Building2,
  MessageSquareHeart,
  LayoutDashboard,
  MessagesSquare,
  Banknote,
} from "lucide-react";
import { ConnectionBadge } from "@/components/ConnectionBadge";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserMenu } from "@/components/UserMenu";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/fraud", label: "Fraud", icon: ShieldAlert },
  { to: "/loans", label: "Loans", icon: Landmark },
  { to: "/advisory", label: "Advisory", icon: HeartHandshake },
  { to: "/branches", label: "Branches", icon: Building2 },
  { to: "/sentiment", label: "Sentiment", icon: MessageSquareHeart },
  { to: "/chat", label: "Assistant", icon: MessagesSquare },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top App Bar (M3) */}
      <header className="sticky top-0 z-30 border-b border-outline-variant bg-surface-container/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1600px] items-center gap-4 px-4 md:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary text-primary-foreground m3-elev-1">
              <Banknote className="h-5 w-5" />
            </span>
            <span className="flex flex-col leading-tight">
              <span className="text-[15px] font-semibold tracking-tight">FinTech Agentic</span>
              <span className="text-[11px] text-on-surface-variant">Banking Operations</span>
            </span>
          </Link>
          <nav className="ml-4 hidden items-center gap-1 lg:flex">
            {NAV.map((n) => {
              const active = n.to === "/" ? pathname === "/" : pathname.startsWith(n.to);
              return (
                <Link
                  key={n.to}
                  to={n.to}
                  className={`m3-state inline-flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-medium transition-colors ${
                    active
                      ? "bg-secondary text-secondary-foreground"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  <n.icon className="h-4 w-4" />
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ConnectionBadge />
            <ThemeToggle />
            <UserMenu />
          </div>
        </div>
        {/* Mobile nav */}
        <nav className="flex gap-1 overflow-x-auto px-3 pb-2 lg:hidden">
          {NAV.map((n) => {
            const active = n.to === "/" ? pathname === "/" : pathname.startsWith(n.to);
            return (
              <Link
                key={n.to}
                to={n.to}
                className={`m3-state inline-flex shrink-0 items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${
                  active
                    ? "bg-secondary text-secondary-foreground"
                    : "text-on-surface-variant"
                }`}
              >
                <n.icon className="h-3.5 w-3.5" />
                {n.label}
              </Link>
            );
          })}
        </nav>
      </header>

      <main className="mx-auto max-w-[1600px] px-4 py-8 md:px-6">{children}</main>

      <footer className="mx-auto max-w-[1600px] px-6 pb-10 pt-4 text-xs text-on-surface-variant">
        Human-in-the-loop required for all consequential agent actions · Full audit trail enforced
      </footer>
    </div>
  );
}
