import { ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/store";
import { Card, CardHeader, Spinner } from "@/components/ui/primitives";
import { PageHeader } from "@/components/ui/PageHeader";
import { NoRun } from "@/components/ui/NoRun";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { TrendLines } from "@/components/charts/TrendLines";
import { ClusterFrequencyBars } from "@/components/charts/ClusterFrequencyBars";
import { SeverityTimeline } from "@/components/charts/SeverityTimeline";

export function AnalyticsPage() {
  const { version } = useApp();
  const { data, loading, error, reload } = useAsync(() => api.analytics(), [version]);

  if (loading && !data) return <Spinner label="Loading analytics…" />;
  if (error && !data) {
    return (
      <>
        <PageHeader title="Analytics" subtitle="Trends, cluster frequency, and service health across your log volume." />
        <LoadFailed onRetry={reload} />
      </>
    );
  }
  if (!data || !data.run) {
    return (
      <>
        <PageHeader title="Analytics" subtitle="Trends, cluster frequency, and service health across your log volume." />
        <NoRun />
      </>
    );
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Analytics"
        subtitle="Trends, cluster frequency, and incident distribution across the analyzed window."
        right={
          <button className="flex h-9 items-center gap-2 rounded-lg border border-hairline px-3 text-sm text-muted hover:text-ink">
            {data.run.source_name}
            <ChevronDown className="h-4 w-4" />
          </button>
        }
      />

      <Card>
        <CardHeader
          title="Error & Warning Trends"
          subtitle="Error- and warning-level event volume per time bucket"
          right={
            <div className="flex items-center gap-4 pt-1 text-xs text-muted">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-sev-critical" /> Errors
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-sev-medium" /> Warnings
              </span>
            </div>
          }
        />
        <div className="px-3 pb-4 pt-3">
          <TrendLines data={data.trends} />
        </div>
      </Card>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Cluster Frequency" subtitle="Highest-volume clusters this window" />
          <div className="px-3 pb-4 pt-2">
            <ClusterFrequencyBars data={data.cluster_frequency} />
          </div>
        </Card>

        <Card>
          <CardHeader title="Incident Timeline" subtitle="Detected incident-cluster volume by severity" />
          <div className="px-3 pb-4 pt-3">
            <SeverityTimeline data={data.timeline} />
          </div>
        </Card>
      </div>
    </div>
  );
}
