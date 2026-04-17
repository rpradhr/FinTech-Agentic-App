import { useQuery } from "@tanstack/react-query";
import { endpoints, apiBaseUrl } from "@/lib/api";
import { Wifi, WifiOff } from "lucide-react";

export function ConnectionBadge() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: endpoints.health,
    refetchInterval: 15_000,
    retry: 0,
  });

  const ok = !!data && !isError;
  return (
    <div
      title={`API: ${apiBaseUrl}`}
      className={`hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium md:inline-flex ${
        isLoading
          ? "border-outline-variant text-on-surface-variant"
          : ok
            ? "border-success/40 bg-success/10 text-success"
            : "border-destructive/40 bg-destructive/10 text-destructive"
      }`}
    >
      {ok ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
      {isLoading ? "Connecting" : ok ? `Online · ${data?.env ?? ""}` : "Offline"}
    </div>
  );
}
