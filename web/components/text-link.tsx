import type { ReactNode } from "react";

export const focusRingClass =
  "rounded-sm focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50";

export const textLinkClass = `${focusRingClass} text-foreground underline decoration-border underline-offset-4 hover:decoration-foreground`;

export function ExternalLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={textLinkClass}>
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}
