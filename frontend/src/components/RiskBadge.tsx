import clsx from "clsx";
import type { RiskLevel } from "@/types";

const config: Record<string, { cls: string; dot: string }> = {
  low:      { cls: "bg-[#e6f4ea] text-[#137333]", dot: "bg-[#34a853]" },
  medium:   { cls: "bg-[#fef7e0] text-[#b06000]", dot: "bg-[#fbbc04]" },
  high:     { cls: "bg-[#fce8e6] text-[#c5221f]", dot: "bg-[#ea4335]" },
  critical: { cls: "bg-[#c5221f] text-white",     dot: "bg-white" },
};

export default function RiskBadge({ level }: { level: RiskLevel | string }) {
  const { cls, dot } = config[level] ?? config.medium;
  return (
    <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium", cls)}>
      <span className={clsx("w-1.5 h-1.5 rounded-full", dot)} />
      {level}
    </span>
  );
}
