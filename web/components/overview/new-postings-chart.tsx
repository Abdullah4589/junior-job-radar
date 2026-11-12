"use client";

import { Area, AreaChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { TrendTooltip } from "@/components/overview/chart-tooltip";
import { chartGrid, chartPrimary, chartTick } from "@/components/overview/chart-theme";
import type { DayPoint } from "@/lib/catalog/overview";

export function NewPostingsChart({ days }: { days: DayPoint[] }) {
  if (days.length === 0) {
    return <p className="text-sm text-muted-foreground">No snapshot days in the catalog yet.</p>;
  }

  return (
    <div className="h-72 w-full" role="img" aria-label="New postings on each snapshot day">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={days} margin={{ top: 24, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={chartGrid} />
          <XAxis dataKey="label" tick={chartTick} tickLine={false} axisLine={false} />
          <YAxis
            allowDecimals={false}
            width={36}
            tick={chartTick}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={TrendTooltip} isAnimationActive={false} />
          <Area
            type="monotone"
            dataKey="new"
            name="New postings"
            stroke={chartPrimary}
            fill={chartPrimary}
            fillOpacity={0.16}
            strokeWidth={2}
            isAnimationActive={false}
            dot={{ r: 4, fill: chartPrimary, stroke: "var(--card)" }}
          >
            <LabelList dataKey="new" position="top" fill="var(--foreground)" fontSize={12} />
          </Area>
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
