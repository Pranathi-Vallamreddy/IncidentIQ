import { Link } from "react-router-dom";
import {
  ArrowDownRight,
  ArrowUpRight,
  ArrowRight,
  Database,
  ShieldAlert,
  ShieldX,
  Boxes,
  Timer,
  Sparkles,
  Download,
  Info,
  FileText,
  Activity,
  GitBranch,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/store";
import { Card, CardHeader, SeverityBadge, Spinner, Button } from "@/components/ui/primitives";
import { PageHeader } from "@/components/ui/PageHeader";
import { NoRun } from "@/components/ui/NoRun";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { RunContext } from "@/components/ui/RunContext";
import { SeverityTimeline } from "@/components/charts/SeverityTimeline";
import { HealthGauge } from "@/components/charts/HealthGauge";
import { cn, fmtGrowth, severityFill } from "@/lib/utils";
import type { Kpi, Pipeline, Severity } from "@/types";

const KPI_ICON: Record<string, typeof Database> = {
  events: Database,
  active: ShieldAlert,
  critical: ShieldX,
  anomalies: Boxes,
  mttr: Timer,
};

const KPI_EXPLAIN: Record<string, string> = {
  events: "Total log lines ingested and parsed by the engine in this run.",
  active: "Incidents not yet resolved (Active, Investigating, or Monitoring).",
  critical: "Incidents scored Critical by the weighted severity engine.",
  anomalies:
    "Clusters flagged as statistically anomalous — peak z-score past the scan-corrected threshold.",
  mttr: "Mean incident duration: average of (last seen − first seen) across incidents.",
};

const HEALTH_EXPLAIN =
  "Health score = 100 − 12 per Critical service − 6 per Degraded service. " +
  "A service is Critical if it has an active Critical incident, Degraded if it has an active High/Medium incident.";

function PipelineStrip({ p }: { p: Pipeline }) {
  const stages = [
    { icon: FileText, label: "Events parsed", value: p.events, sub: p.unparsed ? `${p.unparsed} unparsed` : "structured" },
    { icon: Boxes, label: "Clusters mined", value: p.clusters, sub: "Drain templates" },
    { icon: Activity, label: "Anomalies", value: p.anomalies, sub: "flagged" },
    { icon: ShieldAlert, label: "Incidents", value: p.incidents, sub: "formed" },
    { icon: GitBranch, label: "Correlations", value: p.correlations, sub: "cause links" },
  ];
  return (
    <Card className="mb-4 p-4">
      <div className="mb-3 flex items-center gap-2 text-xs text-muted">
        <Sparkles className="h-3.5 w-3.5 text-violet-400" />
        Analysis pipeline — how raw logs became incidents
      </div>
      <div className="flex flex-wrap items-stretch gap-2">
        {stages.map((s, i) => (
          <div key={s.label} className="flex items-center gap-2">
            <div className="rounded-lg border border-hairline bg-canvas px-4 py-2.5">
              <div className="flex items-center gap-2 text-[11px] text-muted">
                <s.icon className="h-3.5 w-3.5" />
                {s.label}
              </div>
              <div className="mt-1 text-xl font-semibold tabular-nums">{s.value.toLocaleString()}</div>
              <div className="text-[10px] text-faint">{s.sub}</div>
            </div>
            {i < stages.length - 1 && <ArrowRight className="h-4 w-4 shrink-0 text-faint" />}
          </div>
        ))}
      </div>
    </Card>
  );
}

function KpiCard({ kpi }: { kpi: Kpi }) {
  const Icon = KPI_ICON[kpi.key] ?? Database;
  const delta = kpi.delta_pct;
  const up = delta != null && delta >= 0;
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <span className="inline-flex cursor-help items-center gap-1.5 text-xs text-muted" title={KPI_EXPLAIN[kpi.key]}>
          {kpi.label}
          <Info className="h-3 w-3 text-faint" />
        </span>
        <Icon className="h-4 w-4 text-faint" />
      </div>
      <div className="mt-3 text-3xl font-semibold tracking-tight tabular-nums">{kpi.value}</div>
      <div className="mt-2 flex items-center gap-1.5 text-xs">
        {delta != null && (
          <span className={cn("inline-flex items-center gap-0.5", up ? "text-emerald-400" : "text-sev-critical")}>
            {up ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
        <span className="text-faint">{kpi.hint}</span>
      </div>
    </Card>
  );
}

export function DashboardPage() {
  const { version } = useApp();
  const { data, loading, error, reload } = useAsync(() => api.dashboard(), [version]);

  if (loading && !data) return <Spinner label="Analyzing…" />;
  if (error && !data) {
    return (
      <>
        <PageHeader title="Overview" subtitle="Real-time incident intelligence across all services." />
        <LoadFailed onRetry={reload} />
      </>
    );
  }
  if (!data || !data.run) {
    return (
      <>
        <PageHeader title="Overview" subtitle="Real-time incident intelligence across all services." />
        <NoRun />
      </>
    );
  }

  const dist = data.severity_distribution;
  const totalIncidents = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
  const sevOrder: Severity[] = ["Critical", "High", "Medium", "Low"];

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Overview"
        subtitle="Logs are automatically parsed, clustered, scored, correlated, and explained."
        right={
          <a href={api.exportUrl()} title="Download all incidents in this run as CSV">
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4" /> Export incidents (CSV)
            </Button>
          </a>
        }
      />

      <RunContext run={data.run} className="mb-4" />

      {loading && data && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-hairline bg-card px-4 py-2 text-xs text-muted">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Re-analyzing…
        </div>
      )}

      {data.pipeline && <PipelineStrip p={data.pipeline} />}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {data.kpis.map((k) => (
          <KpiCard key={k.key} kpi={k} />
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Incident Timeline"
            subtitle="Events per time bucket from incident clusters, stacked by severity"
            right={
              <div className="flex items-center gap-4 pt-1 text-xs text-muted">
                {sevOrder.map((s) => (
                  <span key={s} className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full" style={{ background: severityFill[s] }} />
                    {s}
                  </span>
                ))}
              </div>
            }
          />
          <div className="px-3 pb-4 pt-3">
            <SeverityTimeline data={data.timeline} />
          </div>
        </Card>

        <Card>
          <CardHeader
            title={
              <span className="inline-flex cursor-help items-center gap-1.5" title={HEALTH_EXPLAIN}>
                System Health
                <Info className="h-3 w-3 text-faint" />
              </span>
            }
            subtitle={data.health_summary}
          />
          <div className="flex flex-col items-center px-5 pb-5 pt-4">
            <HealthGauge score={data.health_score} />
            <div className="mt-5 grid w-full grid-cols-3 gap-2">
              {(["Critical", "Degraded", "Healthy"] as const).map((status) => {
                const n = data.service_health.filter((s) => s.status === status).length;
                const color =
                  status === "Critical" ? "text-sev-critical" : status === "Degraded" ? "text-sev-medium" : "text-emerald-400";
                return (
                  <div key={status} className="rounded-lg border border-hairline bg-card py-2 text-center">
                    <div className={cn("text-lg font-semibold tabular-nums", color)}>{n}</div>
                    <div className="text-[11px] text-muted">{status}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader
            title="Top Anomaly Clusters"
            subtitle="Highest-signal error groups — click to inspect"
            right={
              <Link to="/incidents" className="pt-1 text-xs text-muted hover:text-ink">
                View all
              </Link>
            }
          />
          <div className="space-y-1 p-3">
            {data.top_clusters.map((c) => {
              const inner = (
                <>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-faint">{c.cluster_id}</span>
                      <SeverityBadge severity={c.severity} />
                    </div>
                    <p className="mt-0.5 truncate text-sm text-ink">{c.title}</p>
                    <p className="truncate text-xs text-muted">{c.service}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="tabular-nums text-sm text-ink">{c.count.toLocaleString()}</div>
                    <div className="text-xs text-sev-critical">{fmtGrowth(c.growth_pct, c.baseline_rate)}</div>
                  </div>
                </>
              );
              const cls = "flex items-center justify-between gap-3 rounded-lg px-2 py-2 hover:bg-white/5";
              return c.incident_id ? (
                <Link key={c.cluster_id} to={`/incidents/${c.incident_id}`} className={cls}>
                  {inner}
                </Link>
              ) : (
                <div key={c.cluster_id} className={cls}>
                  {inner}
                </div>
              );
            })}
          </div>
        </Card>

        <Card>
          <CardHeader title="Incident Severity" subtitle={`${totalIncidents} incidents this window`} />
          <div className="space-y-4 p-5">
            {sevOrder.map((s) => {
              const n = dist[s] ?? 0;
              const pct = Math.round((n / totalIncidents) * 100);
              return (
                <div key={s}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <SeverityBadge severity={s} />
                    <span className="tabular-nums text-muted">
                      {n} <span className="text-faint">{pct}%</span>
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, background: severityFill[s] }} />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <Card>
          <CardHeader
            title={
              <span className="inline-flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-violet-400" /> AI Insights
              </span>
            }
            subtitle="Automated correlations across your incidents — click to open"
          />
          <div className="space-y-2 p-3">
            {data.insights.length === 0 && (
              <p className="px-2 py-6 text-center text-sm text-muted">No correlations detected.</p>
            )}
            {data.insights.map((ins, i) => {
              const body = (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-ink">{ins.title}</span>
                    <span className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-muted">{ins.kind}</span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-muted">{ins.detail}</p>
                </>
              );
              const cls = "block rounded-lg border border-hairline bg-card p-3";
              return ins.incident_id ? (
                <Link key={i} to={`/incidents/${ins.incident_id}`} className={cn(cls, "hover:bg-white/5")}>
                  {body}
                </Link>
              ) : (
                <div key={i} className={cls}>
                  {body}
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
