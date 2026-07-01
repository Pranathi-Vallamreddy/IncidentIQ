import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Download, ArrowUpDown } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/store";
import { PageHeader } from "@/components/ui/PageHeader";
import { NoRun } from "@/components/ui/NoRun";
import { LoadFailed } from "@/components/ui/LoadFailed";
import {
  Button,
  Chip,
  ConfidenceBar,
  SeverityBadge,
  Spinner,
  StatusPill,
} from "@/components/ui/primitives";
import { cn, timeAgo } from "@/lib/utils";
import type { Incident, Severity } from "@/types";

const SEVERITIES: (Severity | "All")[] = ["All", "Critical", "High", "Medium", "Low"];
const STATUSES = ["All", "Active", "Investigating", "Monitoring", "Resolved"];
const SEV_RANK: Record<Severity, number> = { Critical: 3, High: 2, Medium: 1, Low: 0 };

type SortKey = "severity" | "confidence" | "recent" | "volume";
const SORTS: { key: SortKey; label: string }[] = [
  { key: "severity", label: "Severity" },
  { key: "confidence", label: "Confidence" },
  { key: "recent", label: "Most recent" },
  { key: "volume", label: "Volume" },
];

function sortIncidents(list: Incident[], key: SortKey): Incident[] {
  const copy = [...list];
  switch (key) {
    case "confidence":
      return copy.sort((a, b) => b.confidence - a.confidence);
    case "recent":
      return copy.sort((a, b) => +new Date(b.last_seen) - +new Date(a.last_seen));
    case "volume":
      return copy.sort((a, b) => b.count - a.count);
    default:
      return copy.sort(
        (a, b) => SEV_RANK[b.severity] - SEV_RANK[a.severity] || b.confidence - a.confidence,
      );
  }
}

export function IncidentsPage() {
  const { version } = useApp();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(() => api.incidents(), [version]);

  const [q, setQ] = useState("");
  const [severity, setSeverity] = useState<Severity | "All">("All");
  const [status, setStatus] = useState("All");
  const [sort, setSort] = useState<SortKey>("severity");

  const all = data ?? [];
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const rows = all.filter((i) => {
      if (severity !== "All" && i.severity !== severity) return false;
      if (status !== "All" && i.status !== status) return false;
      if (needle) {
        const hay = `${i.incident_id} ${i.title} ${i.service ?? ""} ${i.cluster_id}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
    return sortIncidents(rows, sort);
  }, [all, q, severity, status, sort]);

  if (loading && !data) return <Spinner label="Loading incidents…" />;
  if (error && !data) {
    return (
      <>
        <PageHeader
          title="Incidents"
          subtitle="Every detected incident, ranked by severity and confidence."
        />
        <LoadFailed onRetry={reload} />
      </>
    );
  }
  if (!data || data.length === 0) {
    return (
      <>
        <PageHeader
          title="Incidents"
          subtitle="Every detected incident, ranked by severity and confidence."
        />
        <NoRun />
      </>
    );
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Incidents"
        subtitle="Every detected incident, ranked by severity and confidence. Select a row to inspect logs, root cause, and suggested fixes."
        right={
          <a href={api.exportUrl()}>
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4" /> Export CSV
            </Button>
          </a>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search incidents…"
            className="h-9 w-full rounded-lg border border-hairline bg-card pl-9 pr-3 text-sm placeholder:text-faint focus:border-white/20 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-hairline bg-card p-1">
          {SEVERITIES.map((s) => (
            <Chip key={s} active={severity === s} onClick={() => setSeverity(s)}>
              {s}
            </Chip>
          ))}
        </div>

        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="h-9 rounded-lg border border-hairline bg-card px-3 text-sm text-ink focus:outline-none"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s} className="bg-panel">
              {s === "All" ? "All statuses" : s}
            </option>
          ))}
        </select>

        <div className="relative">
          <ArrowUpDown className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="h-9 rounded-lg border border-hairline bg-card pl-8 pr-3 text-sm text-ink focus:outline-none"
          >
            {SORTS.map((s) => (
              <option key={s.key} value={s.key} className="bg-panel">
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-hairline">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-xs text-muted">
              <th className="px-5 py-3 font-medium">Severity</th>
              <th className="px-5 py-3 font-medium">Incident</th>
              <th className="px-5 py-3 font-medium">Service</th>
              <th className="px-5 py-3 font-medium">Cluster</th>
              <th className="px-5 py-3 font-medium">Confidence</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 text-right font-medium">Last seen</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((i) => (
              <tr
                key={i.incident_id}
                onClick={() => navigate(`/incidents/${i.incident_id}`)}
                className="cursor-pointer border-b border-hairline/60 transition-colors last:border-0 hover:bg-white/[0.03]"
              >
                <td className="px-5 py-4">
                  <SeverityBadge severity={i.severity} />
                </td>
                <td className="px-5 py-4">
                  <div className="font-mono text-xs text-faint">{i.incident_id}</div>
                  <div className="mt-0.5 max-w-[420px] truncate text-ink">{i.title}</div>
                </td>
                <td className="px-5 py-4 font-mono text-xs text-muted">{i.service ?? "—"}</td>
                <td className="px-5 py-4 font-mono text-xs text-muted">{i.cluster_id}</td>
                <td className="px-5 py-4">
                  <ConfidenceBar value={i.confidence} />
                </td>
                <td className="px-5 py-4">
                  <StatusPill status={i.status} />
                </td>
                <td className="px-5 py-4 text-right text-xs text-muted">{timeAgo(i.last_seen)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className={cn("mt-4 text-xs text-muted")}>
        Showing {filtered.length} of {all.length} incidents
      </p>
    </div>
  );
}
