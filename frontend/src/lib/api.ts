import type {
  Analytics,
  Dashboard,
  Incident,
  IncidentDetail,
  Explanation,
  Run,
  Sample,
  Settings,
  SettingsUpdate,
} from "@/types";

const BASE = import.meta.env.VITE_API_BASE || "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ status: string; ai_enabled: boolean }>("/health"),
  samples: () => req<Sample[]>("/samples"),
  loadSample: (name: string) =>
    req<Run>(`/samples/${encodeURIComponent(name)}/load`, { method: "POST" }),
  uploadLogs: async (file: File): Promise<Run> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/logs/upload`, { method: "POST", body: form });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json()).detail ?? detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    return res.json();
  },
  latestRun: () => req<Run | null>("/runs/latest"),
  dashboard: () => req<Dashboard>("/dashboard"),
  analytics: () => req<Analytics>("/analytics"),
  incidents: (params: { severity?: string; status?: string; q?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.severity) qs.set("severity", params.severity);
    if (params.status) qs.set("status", params.status);
    if (params.q) qs.set("q", params.q);
    const suffix = qs.toString() ? `?${qs}` : "";
    return req<Incident[]>(`/incidents${suffix}`);
  },
  incident: (id: string) => req<IncidentDetail>(`/incidents/${id}`),
  explain: (id: string) =>
    req<Explanation>(`/incidents/${id}/explain`, { method: "POST" }),
  exportUrl: () => `${BASE}/incidents/export`,
  settings: () => req<Settings>("/settings"),
  updateSettings: (payload: Partial<SettingsUpdate>) =>
    req<Settings>("/settings", { method: "PUT", body: JSON.stringify(payload) }),
};
