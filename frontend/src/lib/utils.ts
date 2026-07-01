import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Severity } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return `${n}`;
}

export function fmtGrowth(pct: number, baselineRate: number): string {
  if (baselineRate < 1e-6 && pct >= 9990) return "NEW";
  if (pct >= 9990) return "▲ 9999%+";
  const sign = pct > 0 ? "▲" : pct < 0 ? "▼" : "";
  return `${sign} ${Math.abs(Math.round(pct))}%`;
}

export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diff = Math.max(0, now - then);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export const severityColor: Record<Severity, string> = {
  Critical: "text-sev-critical",
  High: "text-sev-high",
  Medium: "text-sev-medium",
  Low: "text-sev-low",
};

export const severityDot: Record<Severity, string> = {
  Critical: "bg-sev-critical",
  High: "bg-sev-high",
  Medium: "bg-sev-medium",
  Low: "bg-sev-low",
};

export const severityFill: Record<Severity, string> = {
  Critical: "#f87171",
  High: "#fb923c",
  Medium: "#facc15",
  Low: "#60a5fa",
};

export function statusStyle(status: string): string {
  switch (status) {
    case "Active":
      return "text-sev-critical";
    case "Investigating":
      return "text-sev-high";
    case "Monitoring":
      return "text-sev-medium";
    case "Resolved":
      return "text-emerald-400";
    default:
      return "text-muted";
  }
}
