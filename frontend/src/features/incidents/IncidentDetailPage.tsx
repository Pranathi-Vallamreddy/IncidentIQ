import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Sparkles,
  RefreshCw,
  Wrench,
  GitBranch,
  ArrowDown,
  Activity,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/store";
import { Card, CardHeader, SeverityBadge, StatusPill, Spinner, Button } from "@/components/ui/primitives";
import { NoRun } from "@/components/ui/NoRun";
import { ClusterVolume } from "@/components/charts/ClusterVolume";
import { cn, fmtGrowth, severityColor, severityDot, timeAgo } from "@/lib/utils";
import type { Explanation, Incident } from "@/types";

function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="rounded-lg border border-hairline bg-card px-3 py-2.5">
      <div className="text-[11px] text-muted">{label}</div>
      <div className={cn("mt-0.5 text-sm font-semibold tabular-nums", accent ?? "text-ink")}>{value}</div>
    </div>
  );
}

function ChainNode({
  incident,
  role,
  detail,
  isCurrent,
}: {
  incident: { incident_id: string; title: string; service: string | null; severity: Incident["severity"] };
  role: string;
  detail?: string;
  isCurrent?: boolean;
}) {
  const body = (
    <div
      className={cn(
        "rounded-lg border p-3",
        isCurrent ? "border-white/25 bg-elevated" : "border-hairline bg-card hover:bg-white/5",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wide text-faint">{role}</span>
        <span className={cn("h-2 w-2 rounded-full", severityDot[incident.severity])} />
      </div>
      <div className="mt-1 flex items-center gap-2">
        <span className="font-mono text-xs text-faint">{incident.incident_id}</span>
        <span className="truncate text-sm text-ink">{incident.title}</span>
      </div>
      <div className="mt-0.5 font-mono text-[11px] text-muted">{incident.service ?? "—"}</div>
      {detail && <p className="mt-1.5 text-xs leading-relaxed text-muted">{detail}</p>}
    </div>
  );
  if (isCurrent) return body;
  return (
    <Link to={`/incidents/${incident.incident_id}`} className="block">
      {body}
    </Link>
  );
}

export function IncidentDetailPage() {
  const { id = "" } = useParams();
  const { version } = useApp();
  const { data, loading, error } = useAsync(() => api.incident(id), [id, version]);

  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [explaining, setExplaining] = useState(false);
  const triggeredFor = useRef<string>("");

  async function runExplain() {
    setExplaining(true);
    try {
      setExplanation(await api.explain(id));
    } catch {
      /* keep prior explanation */
    } finally {
      setExplaining(false);
    }
  }

  // Seed from the persisted explanation, else auto-generate once per incident.
  useEffect(() => {
    if (!data) return;
    if (data.explanation) {
      setExplanation(data.explanation);
      triggeredFor.current = id;
    } else if (triggeredFor.current !== id) {
      triggeredFor.current = id;
      setExplanation(null);
      void runExplain();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, id]);

  if (loading && !data) return <Spinner label="Loading incident…" />;
  if (error)
    return (
      <>
        <BackLink />
        <NoRun hint="This incident isn't in the current analysis run. Load logs from the dashboard." />
      </>
    );
  if (!data) return <NoRun />;

  const { incident, cluster, correlations, related_incidents } = data;
  const relById = Object.fromEntries(related_incidents.map((r) => [r.incident_id, r]));
  const upstream = correlations.filter((c) => c.downstream_id === incident.incident_id);
  const downstream = correlations.filter((c) => c.upstream_id === incident.incident_id);
  const maxContribution = Math.max(...cluster.severity_factors.map((f) => f.contribution), 0.001);

  return (
    <div className="animate-fade-in">
      <BackLink />

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm text-faint">{incident.incident_id}</span>
            <SeverityBadge severity={incident.severity} />
            <StatusPill status={incident.status} />
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">{incident.title}</h1>
          <p className="mt-1 font-mono text-sm text-muted">
            {incident.service ?? "unknown service"} · {cluster.cluster_id} · last seen{" "}
            {timeAgo(incident.last_seen)}
          </p>
        </div>
      </div>

      {/* Key metric strip */}
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Metric label="Severity" value={incident.severity} accent={severityColor[incident.severity]} />
        <Metric label="Confidence" value={`${Math.round(incident.confidence * 100)}%`} />
        <Metric
          label="Anomaly z-score"
          value={cluster.zscore.toFixed(1)}
          accent={cluster.is_anomaly ? "text-sev-critical" : "text-ink"}
        />
        <Metric label="Events" value={cluster.count.toLocaleString()} />
        <Metric label="Growth" value={fmtGrowth(cluster.growth_pct, cluster.baseline_rate)} accent="text-sev-high" />
        <Metric label="Log level" value={cluster.level} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* ---- Main column ---- */}
        <div className="space-y-4 lg:col-span-2">
          {/* AI explanation */}
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-violet-400" /> AI Root Cause Analysis
                </span>
              }
              subtitle="The engine computed the analysis; the assistant explains it."
              right={
                <div className="flex items-center gap-2 pt-1">
                  {explanation && (
                    <span
                      className={cn(
                        "rounded px-2 py-0.5 text-[10px] font-medium",
                        explanation.source === "gemini"
                          ? "bg-violet-500/15 text-violet-300"
                          : "bg-white/5 text-muted",
                      )}
                    >
                      {explanation.source === "gemini" ? "Gemini" : "Deterministic"}
                    </span>
                  )}
                  <Button size="sm" variant="ghost" onClick={runExplain} disabled={explaining}>
                    <RefreshCw className={cn("h-3.5 w-3.5", explaining && "animate-spin")} />
                    {explaining ? "Analyzing" : "Regenerate"}
                  </Button>
                </div>
              }
            />
            <div className="space-y-4 p-5">
              {!explanation && explaining && <p className="text-sm text-muted">Generating explanation…</p>}
              {explanation && (
                <>
                  {explanation.source === "deterministic" && (
                    <p className="rounded-lg border border-hairline bg-card px-3 py-2 text-xs text-faint">
                      Generated by the engine's rule-based explainer — set a
                      <span className="font-mono text-muted"> GEMINI_API_KEY </span>
                      to enable live Gemini explanations.
                    </p>
                  )}
                  <p className="text-sm leading-relaxed text-ink">{explanation.summary}</p>
                  <div className="rounded-lg border border-hairline bg-card p-4">
                    <div className="mb-1.5 flex items-center gap-2 text-xs font-medium text-muted">
                      <AlertTriangle className="h-3.5 w-3.5" /> Likely root cause
                    </div>
                    <p className="text-sm leading-relaxed text-ink">{explanation.root_cause}</p>
                  </div>
                  <div>
                    <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted">
                      <Wrench className="h-3.5 w-3.5" /> Suggested fixes
                    </div>
                    <ul className="space-y-2">
                      {explanation.suggested_fixes.map((fix, i) => (
                        <li key={i} className="flex gap-2.5 text-sm text-ink">
                          <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-white/10 text-[10px] text-muted">
                            {i + 1}
                          </span>
                          {fix}
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </div>
          </Card>

          {/* Root cause chain */}
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <GitBranch className="h-4 w-4 text-muted" /> Correlation chain
                </span>
              }
              subtitle="Upstream causes and downstream impact, from the correlation engine."
            />
            <div className="space-y-2 p-5">
              {upstream.map((c) => {
                const inc = relById[c.upstream_id];
                return inc ? (
                  <div key={c.upstream_id} className="space-y-2">
                    <ChainNode incident={inc} role={`Upstream cause · ${c.kind}`} detail={c.detail} />
                    <ArrowDown className="mx-auto h-4 w-4 text-faint" />
                  </div>
                ) : null;
              })}

              <ChainNode incident={incident} role="This incident" isCurrent />

              {downstream.map((c) => {
                const inc = relById[c.downstream_id];
                return inc ? (
                  <div key={c.downstream_id} className="space-y-2">
                    <ArrowDown className="mx-auto h-4 w-4 text-faint" />
                    <ChainNode incident={inc} role={`Downstream impact · ${c.kind}`} detail={c.detail} />
                  </div>
                ) : null;
              })}

              {upstream.length === 0 && downstream.length === 0 && (
                <p className="py-2 text-center text-sm text-muted">
                  No correlated incidents — this appears to be isolated.
                </p>
              )}
            </div>
          </Card>

          {/* Timeline */}
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Activity className="h-4 w-4 text-muted" /> Cluster volume timeline
                </span>
              }
              subtitle="Events per time bucket; the peak bucket is highlighted."
            />
            <div className="px-3 pb-4 pt-2">
              <ClusterVolume buckets={cluster.buckets} severity={incident.severity} />
            </div>
          </Card>

          {/* Template + normalized */}
          <Card>
            <CardHeader title="Detected template" subtitle="Mined pattern and a normalized example." />
            <div className="space-y-3 p-5">
              <CodeBlock label="Template pattern" text={cluster.template} tone="template" />
              <CodeBlock label="Normalized example" text={cluster.normalized_example} tone="norm" />
            </div>
          </Card>

          {/* Sample raw logs */}
          <Card>
            <CardHeader
              title="Sample raw log lines"
              subtitle={`${cluster.example_logs.length} representative events from this cluster.`}
            />
            <div className="p-5">
              <div className="scrollbar-thin max-h-72 overflow-auto rounded-lg border border-hairline bg-canvas p-3 font-mono text-xs leading-relaxed text-muted">
                {cluster.example_logs.map((line, i) => (
                  <div key={i} className="whitespace-pre-wrap break-all border-b border-hairline/40 py-1 last:border-0">
                    {line}
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* ---- Side column ---- */}
        <div className="space-y-4">
          {/* Cluster statistics */}
          <Card>
            <CardHeader title="Cluster statistics" subtitle={cluster.cluster_id} />
            <div className="grid grid-cols-2 gap-2 p-4">
              <Metric label="Total events" value={cluster.count.toLocaleString()} />
              <Metric label="Recent events" value={cluster.recent_count.toLocaleString()} />
              <Metric label="Anomaly score" value={cluster.anomaly_score.toFixed(2)} />
              <Metric label="Z-score" value={cluster.zscore.toFixed(2)} />
              <Metric label="Baseline / bucket" value={cluster.baseline_rate.toFixed(1)} />
              <Metric label="Tokens" value={String(cluster.token_count)} />
            </div>
            <div className="px-4 pb-4">
              <div className="mb-2 text-[11px] text-muted">Affected services</div>
              <div className="space-y-1.5">
                {Object.entries(cluster.services)
                  .sort((a, b) => b[1] - a[1])
                  .map(([svc, n]) => (
                    <div key={svc} className="flex items-center justify-between text-xs">
                      <span className="font-mono text-ink">{svc}</span>
                      <span className="tabular-nums text-muted">{n.toLocaleString()}</span>
                    </div>
                  ))}
              </div>
            </div>
          </Card>

          {/* Severity calculation */}
          <Card>
            <CardHeader
              title="Severity calculation"
              subtitle={`Weighted score ${(cluster.severity_score * 100).toFixed(0)}/100 → ${cluster.severity}`}
            />
            <div className="space-y-3 p-5">
              {cluster.severity_factors.map((f) => (
                <div key={f.name}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="capitalize text-ink">{f.name}</span>
                    <span className="tabular-nums text-muted">
                      {(f.value * 100).toFixed(0)}% × {f.weight.toFixed(2)}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-ink"
                      style={{ width: `${(f.contribution / maxContribution) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
              <div className="flex items-center justify-between border-t border-hairline pt-3 text-sm">
                <span className="text-muted">Confidence</span>
                <span className="font-semibold tabular-nums">{Math.round(cluster.confidence * 100)}%</span>
              </div>
            </div>
          </Card>

          {/* Correlated incidents */}
          <Card>
            <CardHeader title="Correlated incidents" subtitle={`${related_incidents.length} linked`} />
            <div className="space-y-1 p-3">
              {related_incidents.length === 0 && (
                <p className="px-2 py-4 text-center text-sm text-muted">None.</p>
              )}
              {related_incidents.map((r) => (
                <Link
                  key={r.incident_id}
                  to={`/incidents/${r.incident_id}`}
                  className="flex items-center justify-between gap-3 rounded-lg px-2 py-2 hover:bg-white/5"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={cn("h-2 w-2 rounded-full", severityDot[r.severity])} />
                      <span className="font-mono text-xs text-faint">{r.incident_id}</span>
                    </div>
                    <div className="mt-0.5 truncate text-sm text-ink">{r.title}</div>
                  </div>
                  <span className="shrink-0 font-mono text-[11px] text-muted">{r.service}</span>
                </Link>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      to="/incidents"
      className="mb-5 inline-flex items-center gap-2 text-sm text-muted hover:text-ink"
    >
      <ArrowLeft className="h-4 w-4" /> Back to incidents
    </Link>
  );
}

function CodeBlock({ label, text, tone }: { label: string; text: string; tone: "template" | "norm" }) {
  return (
    <div>
      <div className="mb-1.5 text-[11px] text-muted">{label}</div>
      <pre
        className={cn(
          "scrollbar-thin overflow-x-auto rounded-lg border border-hairline bg-canvas p-3 font-mono text-xs leading-relaxed",
          tone === "template" ? "text-emerald-300/90" : "text-sky-300/90",
        )}
      >
        {text}
      </pre>
    </div>
  );
}
