import { FileText } from "lucide-react";
import { timeAgo } from "@/lib/utils";
import type { Run } from "@/types";

function fmtWindow(startIso: string, endIso: string): string {
  const s = new Date(startIso);
  const e = new Date(endIso);
  const day = s.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  const t = (d: Date) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${day} · ${t(s)}–${t(e)}`;
}

/** The dataset/window/"analyzed X ago" indicator shown at the top of data pages. */
export function RunContext({ run, className }: { run: Run; className?: string }) {
  return (
    <div
      className={
        "flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-hairline bg-card px-4 py-2.5 text-xs " +
        (className ?? "")
      }
    >
      <span className="inline-flex items-center gap-1.5 text-muted">
        <FileText className="h-3.5 w-3.5" />
        <span className="font-mono text-ink">{run.source_name}</span>
      </span>
      <span className="text-faint">·</span>
      <span className="text-muted">{run.event_count.toLocaleString()} events</span>
      <span className="text-faint">·</span>
      <span className="text-muted">{fmtWindow(run.window_start, run.window_end)}</span>
      <span className="text-faint">·</span>
      <span className="text-muted">analyzed {timeAgo(run.created_at)}</span>
    </div>
  );
}
