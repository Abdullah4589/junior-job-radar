import { textLinkClass } from "@/components/text-link";
import { SOURCE_META } from "@/lib/catalog/labels";
import { SOURCES } from "@/lib/catalog/types";

export function SiteFooter() {
  return (
    <footer className="mt-4 border-t border-border/80">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm leading-6 text-muted-foreground sm:px-6">
        <p>
          Sources:{" "}
          {SOURCES.map((source, index) => (
            <span key={source}>
              {index > 0 ? ", " : null}
              <a href={SOURCE_META[source].href} className={textLinkClass}>
                {SOURCE_META[source].name}
              </a>
            </span>
          ))}
          . This page is built from the committed catalog. Each posting links back to the board.
        </p>
        <p>Built by Abdullah in Karachi. Job text stays with the boards and the employers.</p>
      </div>
    </footer>
  );
}
