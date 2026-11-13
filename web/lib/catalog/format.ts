const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] as const;

/** Format a `YYYY-MM-DD` date, or the date prefix of an ISO timestamp. */
export function formatIsoDate(iso: string, includeYear = true): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:$|T)/.exec(iso);
  if (!match) {
    return iso;
  }
  const year = match[1] ?? iso;
  const month = MONTHS[Number(match[2]) - 1];
  const day = Number(match[3]);
  if (!month || !Number.isInteger(day)) {
    return iso;
  }
  return includeYear ? `${day} ${month} ${year}` : `${day} ${month}`;
}
