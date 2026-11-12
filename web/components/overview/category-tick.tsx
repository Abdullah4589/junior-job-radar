import type { YAxisTickContentProps } from "recharts";

function coordinate(value: number | string): number {
  return typeof value === "number" ? value : Number(value);
}

/** Single-line category labels. The default tick wraps long names into the next row. */
export function CategoryTick({ x, y, payload }: YAxisTickContentProps) {
  return (
    <text
      x={coordinate(x)}
      y={coordinate(y)}
      dy={4}
      textAnchor="end"
      fill="var(--muted-foreground)"
      fontSize={12}
    >
      {payload.value}
    </text>
  );
}
