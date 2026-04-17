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
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/fraud", label: "Fraud", icon: ShieldAlert },
  { to: "/loans", label: "Loans", icon: Landmark },
  { to: "/advisory", label: "Advisory", icon: HeartHandshake },
  { to: "/branches", label: "Branches", icon: Building2 },
  { to: "/sentiment", label: "Sentiment", icon: MessageSquareHeart },
  { to: "/chat", label: "Assistant", icon: MessagesSquare },
] as const;

function AppSidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { state } = useSidebar();
  const collapsed = state === "collapsed";

  return (
    <Sidebar collapsible="icon" className="border-r border-outline-variant">
      <SidebarHeader className="border-b border-outline-variant">
        <Link to="/" className="flex items-center gap-2.5 px-1 py-1.5">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground m3-elev-1">
            <Banknote className="h-5 w-5" />
          </span>
          {!collapsed && (
            <span className="flex flex-col leading-tight">
              <span className="text-[15px] font-semibold tracking-tight">FinTechAI</span>
              <span className="text-[11px] text-on-surface-variant">Banking Operations</span>
            </span>
          )}
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Agents</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV.map((n) => {
                const active = n.to === "/" ? pathname === "/" : pathname.startsWith(n.to);
                return (
                  <SidebarMenuItem key={n.to}>
                    <SidebarMenuButton asChild isActive={active} tooltip={n.label}>
                      <Link to={n.to}>
                        <n.icon className="h-4 w-4" />
                        <span>{n.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background text-foreground">
        <AppSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-outline-variant bg-surface-container/80 px-4 backdrop-blur md:px-6">
            <SidebarTrigger className="-ml-1" />
            <div className="ml-auto flex items-center gap-2">
              <ConnectionBadge />
              <ThemeToggle />
              <UserMenu />
            </div>
          </header>

          <main className="mx-auto w-full max-w-[1600px] px-4 py-8 md:px-6">{children}</main>

          <footer className="mx-auto w-full max-w-[1600px] px-6 pb-10 pt-4 text-xs text-on-surface-variant">
            Human-in-the-loop required for all consequential agent actions · Full audit trail enforced
          </footer>
        </div>
      </div>
    </SidebarProvider>
  );
}
