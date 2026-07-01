import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Bucket, Severity } from "@/types";
import { fmtTime, severityFill } from "@/lib/utils";

export function ClusterVolume({ buckets, severity }: { buckets: Bucket[]; severity: Severity }) {
  const rows = buckets.map((b) => ({ label: fmtTime(b.ts), count: b.count }));
  const peak = Math.max(...rows.map((r) => r.count), 0);
  const color = severityFill[severity];

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: -18, bottom: 0 }} barCategoryGap={2}>
        <XAxis
          dataKey="label"
          tick={{ fill: "#5f5f68", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          interval={Math.max(0, Math.floor(rows.length / 10) - 1)}
        />
        <YAxis tick={{ fill: "#5f5f68", fontSize: 10 }} axisLine={false} tickLine={false} width={36} />
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
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {rows.map((r, idx) => (
            <Cell key={idx} fill={r.count === peak && peak > 0 ? color : "#3f3f46"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
