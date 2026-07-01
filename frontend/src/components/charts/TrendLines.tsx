import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendPoint } from "@/types";
import { fmtTime } from "@/lib/utils";

export function TrendLines({ data }: { data: TrendPoint[] }) {
  const rows = data.map((p) => ({ ...p, label: fmtTime(p.ts) }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={rows} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="err" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f87171" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#f87171" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="warn" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#facc15" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#facc15" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="label"
          tick={{ fill: "#5f5f68", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          interval={Math.max(0, Math.floor(rows.length / 12) - 1)}
        />
        <YAxis tick={{ fill: "#5f5f68", fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
        <Tooltip
          cursor={{ stroke: "#26262b" }}
          contentStyle={{ background: "#151518", border: "1px solid #26262b", borderRadius: 10, fontSize: 12 }}
          labelStyle={{ color: "#f4f4f5" }}
        />
        <Area type="monotone" dataKey="errors" stroke="#f87171" strokeWidth={2} fill="url(#err)" />
        <Area type="monotone" dataKey="warnings" stroke="#facc15" strokeWidth={2} fill="url(#warn)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
