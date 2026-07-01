import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TimelinePoint } from "@/types";
import { fmtTime, severityFill } from "@/lib/utils";

export function SeverityTimeline({ data }: { data: TimelinePoint[] }) {
  const rows = data.map((p) => ({ ...p, label: fmtTime(p.ts) }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: -16, bottom: 0 }} barCategoryGap={3}>
        <XAxis
          dataKey="label"
          tick={{ fill: "#5f5f68", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          interval={Math.max(0, Math.floor(rows.length / 12) - 1)}
        />
        <YAxis tick={{ fill: "#5f5f68", fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
          contentStyle={{
            background: "#151518",
            border: "1px solid #26262b",
            borderRadius: 10,
            fontSize: 12,
          }}
          labelStyle={{ color: "#f4f4f5" }}
        />
        <Bar dataKey="Critical" stackId="s" fill={severityFill.Critical} radius={[0, 0, 0, 0]} />
        <Bar dataKey="High" stackId="s" fill={severityFill.High} />
        <Bar dataKey="Medium" stackId="s" fill={severityFill.Medium} />
        <Bar dataKey="Low" stackId="s" fill={severityFill.Low} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
