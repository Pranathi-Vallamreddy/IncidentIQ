import { Printer, FileDown, Mail, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/store";
import { Card, CardHeader, Button, Spinner, SeverityBadge } from "@/components/ui/primitives";
import { PageHeader } from "@/components/ui/PageHeader";
import { NoRun } from "@/components/ui/NoRun";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { TrendLines } from "@/components/charts/TrendLines";
import { severityFill } from "@/lib/utils";
import type { Dashboard, Severity } from "@/types";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function execSummary(d: Dashboard): string {
  const run = d.run!;
  const critical = d.severity_distribution.Critical ?? 0;
  const total = Object.values(d.severity_distribution).reduce((a, b) => a + b, 0);
  const services = new Set(d.service_health.map((s) => s.service)).size;
  const mttr = d.kpis.find((k) => k.key === "mttr")?.value ?? "—";
  const cascade = d.insights.find((i) => i.kind === "Correlation");

  let text =
    `This window analyzed ${run.event_count.toLocaleString()} log events, which the engine ` +
    `compressed into ${run.cluster_count} clusters. ${total} incidents were detected across ` +
    `${services} services, ${critical} of them critical. Mean incident span was ${mttr}.`;
  if (cascade) text += ` ${cascade.detail}`;
  return text;
}

export function ReportsPage() {
  const { version } = useApp();
  const dash = useAsync(() => api.dashboard(), [version]);
  const analytics = useAsync(() => api.analytics(), [version]);

  if ((dash.loading && !dash.data) || (analytics.loading && !analytics.data))
    return <Spinner label="Generating report…" />;
  if (dash.error && !dash.data) {
    return (
      <>
        <PageHeader title="Reports" subtitle="Shareable, export-ready incident reports and postmortems." />
        <LoadFailed onRetry={dash.reload} />
      </>
    );
  }
  const d = dash.data;
  if (!d || !d.run) {
    return (
      <>
        <PageHeader title="Reports" subtitle="Shareable, export-ready incident reports and postmortems." />
        <NoRun />
      </>
    );
  }

  const run = d.run;
  const rpt = `RPT-${1000 + run.id}`;
  const total = Object.values(d.severity_distribution).reduce((a, b) => a + b, 0) || 1;
  const critical = d.severity_distribution.Critical ?? 0;
  const mttr = d.kpis.find((k) => k.key === "mttr")?.value ?? "—";
  const sevOrder: Severity[] = ["Critical", "High", "Medium", "Low"];

  const stats = [
    { label: "Incidents", value: String(total) },
    { label: "Critical", value: String(critical) },
    { label: "MTTR", value: mttr },
    { label: "Events analyzed", value: d.kpis.find((k) => k.key === "events")?.value ?? "—" },
  ];

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Reports"
        subtitle="Shareable, export-ready incident reports and postmortems."
        right={
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            <FileDown className="h-4 w-4" /> New report
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between border-b border-hairline px-6 py-4">
            <div className="flex items-center gap-3">
              <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-400">
                Published
              </span>
              <span className="text-xs text-muted">
                {fmtDate(run.window_start)} – {fmtDate(run.window_end)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={() => window.print()}>
                <FileDown className="h-3.5 w-3.5" /> PDF
              </Button>
              <Button size="sm" variant="ghost" onClick={() => window.print()}>
                <Printer className="h-3.5 w-3.5" /> Print
              </Button>
              <Button size="sm" variant="ghost">
                <Mail className="h-3.5 w-3.5" /> Email
              </Button>
            </div>
          </div>

          <div className="p-6">
            <h2 className="text-xl font-semibold">Reliability Review — {run.source_name}</h2>

            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {stats.map((s) => (
                <div key={s.label} className="rounded-lg border border-hairline bg-card px-4 py-3">
                  <div className="text-xs text-muted">{s.label}</div>
                  <div className="mt-1 text-2xl font-semibold tabular-nums">{s.value}</div>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-xl border border-hairline bg-card p-5">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                <Sparkles className="h-4 w-4 text-violet-400" /> Executive summary
              </div>
              <p className="text-sm leading-relaxed text-muted">{execSummary(d)}</p>
            </div>

            {analytics.data && (
              <div className="mt-6">
                <div className="mb-2 text-sm font-medium">Incident volume</div>
                <TrendLines data={analytics.data.trends} />
              </div>
            )}

            <div className="mt-6">
              <div className="mb-3 text-sm font-medium">Severity breakdown</div>
              <div className="space-y-3">
                {sevOrder.map((s) => {
                  const n = d.severity_distribution[s] ?? 0;
                  const pct = Math.round((n / total) * 100);
                  return (
                    <div key={s}>
                      <div className="mb-1.5 flex items-center justify-between text-sm">
                        <SeverityBadge severity={s} />
                        <span className="tabular-nums text-muted">{n}</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: severityFill[s] }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </Card>

        <Card className="h-fit">
          <CardHeader title="Report details" subtitle="Generated from the current analysis run" />
          <div className="space-y-3 p-5 text-sm">
            {[
              ["Report ID", rpt],
              ["Status", "Published"],
              ["Source", run.source_name],
              ["Incidents", String(total)],
              ["MTTR", mttr],
              ["Events", run.event_count.toLocaleString()],
              ["Clusters", String(run.cluster_count)],
              ["Generated", fmtDate(run.created_at)],
              ["Author", "SRE Team"],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between">
                <span className="text-muted">{k}</span>
                <span className="font-mono text-xs text-ink">{v}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
