"use client";

import { Bar, BarChart, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CategoryTick } from "@/components/overview/category-tick";
import { CountTooltip } from "@/components/overview/chart-tooltip";
import { chartPrimary } from "@/components/overview/chart-theme";
import type { SkillRow } from "@/lib/catalog/overview";

export function SkillsChart({ skills }: { skills: SkillRow[] }) {
  if (skills.length === 0) {
    return <p className="text-sm text-muted-foreground">No skills were extracted for this catalog.</p>;
  }

  return (
    <div
      className="w-full"
      style={{ height: Math.max(280, skills.length * 28) }}
      role="img"
      aria-label="Most common skills in the catalog"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={skills}
          layout="vertical"
          margin={{ top: 4, right: 36, left: 4, bottom: 4 }}
          barSize={10}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="skill"
            width={132}
            interval={0}
            tick={CategoryTick}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={CountTooltip} isAnimationActive={false} cursor={{ fill: "var(--muted)" }} />
          <Bar dataKey="count" fill={chartPrimary} radius={[0, 6, 6, 0]} isAnimationActive={false}>
            <LabelList dataKey="count" position="right" fill="var(--foreground)" fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
