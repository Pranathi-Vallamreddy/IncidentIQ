// Mirror of backend Pydantic DTOs (app/schemas.py).

export type Severity = "Critical" | "High" | "Medium" | "Low";

export interface Run {
  id: number;
  source_name: string;
  event_count: number;
  parsed_count: number;
  unparsed_count: number;
  cluster_count: number;
  incident_count: number;
  window_start: string;
  window_end: string;
  created_at: string;
}

export interface Sample {
  name: string;
  size_kb: number;
  fmt: string;
  description: string;
}

export interface Incident {
  incident_id: string;
  cluster_id: string;
  title: string;
  service: string | null;
  severity: Severity;
  confidence: number;
  status: string;
  anomaly_score: number;
  growth_pct: number;
  baseline_rate: number;
  count: number;
  first_seen: string;
  last_seen: string;
  correlated_ids: string[];
}

export interface Bucket {
  ts: string;
  count: number;
}

export interface SeverityFactor {
  name: string;
  value: number;
  weight: number;
  contribution: number;
}

export interface ClusterDetail {
  cluster_id: string;
  template: string;
  normalized_example: string;
  level: string;
  count: number;
  token_count: number;
  services: Record<string, number>;
  example_logs: string[];
  buckets: Bucket[];
  anomaly_score: number;
  zscore: number;
  is_anomaly: boolean;
  growth_pct: number;
  baseline_rate: number;
  recent_count: number;
  severity: Severity;
  severity_score: number;
  confidence: number;
  severity_factors: SeverityFactor[];
}

export interface Correlation {
  upstream_id: string;
  downstream_id: string;
  kind: string;
  detail: string;
  lag_seconds: number;
}

export interface Explanation {
  source: "gemini" | "deterministic";
  summary: string;
  root_cause: string;
  suggested_fixes: string[];
}

export interface IncidentDetail {
  incident: Incident;
  cluster: ClusterDetail;
  correlations: Correlation[];
  related_incidents: Incident[];
  explanation: Explanation | null;
}

export interface Kpi {
  key: string;
  label: string;
  value: string;
  raw: number;
  delta_pct: number | null;
  hint: string;
}

export interface TimelinePoint {
  ts: string;
  Critical: number;
  High: number;
  Medium: number;
  Low: number;
}

export interface ServiceHealth {
  service: string;
  status: "Critical" | "Degraded" | "Healthy";
  incidents: number;
}

export interface TopCluster {
  cluster_id: string;
  incident_id: string | null;
  title: string;
  service: string | null;
  severity: Severity;
  count: number;
  growth_pct: number;
  baseline_rate: number;
}

export interface Insight {
  kind: string;
  title: string;
  detail: string;
  incident_id: string | null;
}

export interface Pipeline {
  events: number;
  parsed: number;
  unparsed: number;
  clusters: number;
  anomalies: number;
  incidents: number;
  correlations: number;
}

export interface Dashboard {
  run: Run | null;
  kpis: Kpi[];
  timeline: TimelinePoint[];
  health_score: number;
  health_summary: string;
  service_health: ServiceHealth[];
  top_clusters: TopCluster[];
  severity_distribution: Record<string, number>;
  insights: Insight[];
  pipeline: Pipeline | null;
}

export interface TrendPoint {
  ts: string;
  errors: number;
  warnings: number;
}

export interface FreqBar {
  cluster_id: string;
  count: number;
}

export interface Analytics {
  run: Run | null;
  trends: TrendPoint[];
  cluster_frequency: FreqBar[];
  timeline: TimelinePoint[];
}

export interface Settings {
  anomaly_sensitivity: number;
  ai_root_cause: boolean;
  ai_available: boolean;
  ai_model: string;
}

export type SettingsUpdate = Pick<Settings, "anomaly_sensitivity" | "ai_root_cause">;
