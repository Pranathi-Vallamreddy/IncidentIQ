import { NavLink } from "react-router-dom";
import { Activity, LayoutDashboard, ShieldAlert, BarChart3, FileText, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { useApp } from "@/store";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/incidents", label: "Incidents", icon: ShieldAlert, end: false },
  { to: "/analytics", label: "Analytics", icon: BarChart3, end: false },
  { to: "/reports", label: "Reports", icon: FileText, end: false },
  { to: "/settings", label: "Settings", icon: Settings, end: false },
];

export function Sidebar() {
  const { version } = useApp();
  const dash = useAsync(() => api.dashboard(), [version]);
  const run = dash.data?.run;

  return (
    <aside className="flex w-[248px] shrink-0 flex-col border-r border-hairline bg-panel">
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-hairline bg-card">
          <Activity className="h-5 w-5 text-ink" />
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight">IncidentIQ</div>
          <div className="text-xs text-muted">Incident Intelligence</div>
        </div>
      </div>

      <nav className="mt-2 flex flex-col gap-1 px-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive ? "bg-elevated text-ink" : "text-muted hover:text-ink hover:bg-white/5",
              )
            }
          >
            <Icon className="h-[18px] w-[18px]" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto p-3">
        <div className="rounded-xl border border-hairline bg-card p-4">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-pulse2 rounded-full bg-emerald-400" />
            </span>
            <span className="text-sm font-medium">Live analysis</span>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-muted">
            {run
              ? `Analyzed ${run.event_count.toLocaleString()} events • ${run.cluster_count} clusters from ${run.source_name}.`
              : "No data yet. Upload logs to start the engine."}
          </p>
        </div>
      </div>
    </aside>
  );
}
