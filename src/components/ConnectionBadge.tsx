import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { endpoints, apiBaseUrl, demoMode } from "@/lib/api";
import { Wifi, WifiOff, Sparkles } from "lucide-react";
import { toast } from "sonner";

export function ConnectionBadge() {
  const qc = useQueryClient();
  const [demo, setDemo] = useState(demoMode.isOn());

  const { data, isError, isLoading } = useQuery({
    queryKey: ["health", demo],
    queryFn: endpoints.health,
    refetchInterval: 15_000,
    retry: 0,
  });

  useEffect(() => {
    setDemo(demoMode.isOn());
  }, []);

  const toggle = () => {
    const next = !demo;
    demoMode.set(next);
    setDemo(next);
    qc.invalidateQueries();
    toast.message(next ? "Demo mode on — using mock data" : "Demo mode off — calling backend");
  };

  if (demo) {
    return (
      <button
        onClick={toggle}
        title="Click to switch to live backend"
        className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-primary/12 px-2.5 py-1 text-xs font-semibold text-primary"
      >
        <Sparkles className="h-3.5 w-3.5" />
        Demo mode
      </button>
    );
  }

  const ok = !!data && !isError;
  return (
    <button
      onClick={toggle}
      title={`API: ${apiBaseUrl} · click to switch to demo mode`}
      className={`hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium md:inline-flex ${
        isLoading
          ? "border-outline-variant text-on-surface-variant"
          : ok
            ? "border-success/40 bg-success/10 text-success"
            : "border-destructive/40 bg-destructive/10 text-destructive"
      }`}
    >
      {ok ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
      {isLoading ? "Connecting" : ok ? `Live · ${data?.env ?? ""}` : "Offline"}
    </button>
  );
}
