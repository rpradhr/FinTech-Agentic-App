import {
  Outlet,
  Link,
  createRootRouteWithContext,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { AppShell } from "@/components/AppShell";

import appCss from "../styles.css?url";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="m3-display text-foreground">404</h1>
        <h2 className="mt-2 m3-title text-on-surface">Page not found</h2>
        <p className="mt-2 text-sm text-on-surface-variant">
          This route doesn't exist in the FinTech Agentic console.
        </p>
        <Link
          to="/"
          className="m3-state mt-6 inline-flex h-10 items-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground"
        >
          Back to overview
        </Link>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "FinTech Agentic — Banking Operations Console" },
      {
        name: "description",
        content:
          "Multi-agent banking operations console: fraud, loans, advisory, branches, sentiment — with human-in-the-loop controls.",
      },
      { name: "author", content: "FinTech Agentic" },
      { property: "og:title", content: "FinTech Agentic — Banking Operations" },
      {
        property: "og:description",
        content:
          "Material 3 console for fraud detection, loan review, advisory, branch monitoring, and sentiment.",
      },
      { property: "og:type", content: "website" },
    ],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell>
        <Outlet />
      </AppShell>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  );
}
