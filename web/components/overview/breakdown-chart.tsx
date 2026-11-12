"use client";

import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CategoryTick } from "@/components/overview/category-tick";
import { CountTooltip } from "@/components/overview/chart-tooltip";
import { chartPrimary, workplaceFill } from "@/components/overview/chart-theme";
import type { BreakdownRow } from "@/lib/catalog/overview";

export function BreakdownChart({
  rows,
  label,
  colorByKey = false,
}: {
  rows: BreakdownRow[];
  label: string;
  colorByKey?: boolean;
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">Nothing to chart yet.</p>;
  }

  return (
    <div
      className="w-full"
      style={{ height: Math.max(220, rows.length * 36) }}
      role="img"
      aria-label={label}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 4, right: 88, left: 8, bottom: 4 }}
          barSize={14}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            width={96}
            interval={0}
            tick={CategoryTick}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={CountTooltip} isAnimationActive={false} cursor={{ fill: "var(--muted)" }} />
          <Bar dataKey="count" radius={[0, 6, 6, 0]} isAnimationActive={false}>
            {rows.map((row) => (
              <Cell
                key={row.key}
                fill={colorByKey ? (workplaceFill[row.key] ?? chartPrimary) : chartPrimary}
              />
            ))}
            <LabelList dataKey="detail" position="right" fill="var(--foreground)" fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
