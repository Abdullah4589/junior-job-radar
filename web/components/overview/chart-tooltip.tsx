"use client";

import type { TooltipContentProps } from "recharts";

function TooltipFrame({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-lg bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md ring-1 ring-foreground/10">
      <p className="font-medium">{title}</p>
      {lines.map((line) => (
        <p key={line} className="text-muted-foreground">
          {line}
        </p>
      ))}
    </div>
  );
}

type TrendRow = {
  label?: string;
  new?: number;
  seenAgain?: number;
  collected?: number;
};

type CountRow = {
  label?: string;
  skill?: string;
  count?: number;
  shareLabel?: string;
};

function rowFrom<T>(props: TooltipContentProps): T | undefined {
  const entry = props.payload[0];
  if (!props.active || entry === undefined) {
    return undefined;
  }
  return entry.payload as T;
}

export function TrendTooltip(props: TooltipContentProps) {
  const row = rowFrom<TrendRow>(props);
  if (!row || row.label === undefined || row.new === undefined) {
    return null;
  }
  return (
    <TooltipFrame
      title={row.label}
      lines={[
        `${row.new} new`,
        `${row.seenAgain ?? 0} seen again`,
        `${row.collected ?? 0} collected that day`,
      ]}
    />
  );
}

export function CountTooltip(props: TooltipContentProps) {
  const row = rowFrom<CountRow>(props);
  const title = row?.label ?? row?.skill;
  if (!row || title === undefined || row.count === undefined || row.shareLabel === undefined) {
    return null;
  }
  return <TooltipFrame title={title} lines={[`${row.count} postings · ${row.shareLabel}`]} />;
}
