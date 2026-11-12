const SOURCES = [
  { name: "Remotive", href: "https://remotive.com" },
  { name: "Remote OK", href: "https://remoteok.com" },
  { name: "Arbeitnow", href: "https://www.arbeitnow.com" },
] as const;

export function SiteFooter() {
  return (
    <footer className="mt-4 border-t border-border/80">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-8 text-sm leading-6 text-muted-foreground">
        <p>
          Sources:{" "}
          {SOURCES.map((source, index) => (
            <span key={source.href}>
              {index > 0 ? ", " : null}
              <a
                href={source.href}
                className="text-foreground underline decoration-border underline-offset-4 hover:decoration-foreground"
              >
                {source.name}
              </a>
            </span>
          ))}
          . This page is built from the committed catalog.
        </p>
        <p>Built by Abdullah in Karachi. Job text stays with the boards and the employers.</p>
      </div>
    </footer>
  );
}
