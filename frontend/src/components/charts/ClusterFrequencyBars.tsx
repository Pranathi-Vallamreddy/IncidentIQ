import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FreqBar } from "@/types";

export function ClusterFrequencyBars({ data }: { data: FreqBar[] }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 34)}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
        barCategoryGap={8}
      >
        <XAxis type="number" tick={{ fill: "#5f5f68", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis
          type="category"
          dataKey="cluster_id"
          tick={{ fill: "#8a8a94", fontSize: 11, fontFamily: "monospace" }}
          axisLine={false}
          tickLine={false}
          width={64}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
          contentStyle={{ background: "#151518", border: "1px solid #26262b", borderRadius: 10, fontSize: 12 }}
          labelStyle={{ color: "#f4f4f5" }}
        />
        <Bar dataKey="count" fill="#71717a" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
