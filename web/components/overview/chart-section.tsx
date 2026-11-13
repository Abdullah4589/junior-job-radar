import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { SrTable } from "@/components/overview/sr-table";

export function ChartSection({
  id,
  title,
  description,
  children,
  table,
}: {
  id: string;
  title: string;
  description: string;
  children: ReactNode;
  table: {
    caption: string;
    headers: string[];
    rows: string[][];
  };
}) {
  return (
    <section aria-labelledby={id}>
      <Card>
        <CardHeader>
          <h2 id={id} className="scroll-mt-6 font-heading text-lg leading-snug font-medium tracking-tight">
            {title}
          </h2>
          <CardDescription className="max-w-2xl text-sm leading-6">{description}</CardDescription>
        </CardHeader>
        <CardContent>
          {children}
          <SrTable caption={table.caption} headers={table.headers} rows={table.rows} />
        </CardContent>
      </Card>
    </section>
  );
}
