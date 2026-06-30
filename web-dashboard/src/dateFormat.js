const DISPLAY_TZ = "Etc/GMT-3";

const DISPLAY_FORMATTER = new Intl.DateTimeFormat("en-US", {
  timeZone: DISPLAY_TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

export function normalizeIsoDateString(value) {
  return String(value).replace(/\.(\d{3})\d+/, ".$1");
}

export function formatDisplayDate(value) {
  if (!value) return "unknown";
  const date = new Date(normalizeIsoDateString(value));
  if (Number.isNaN(date.getTime())) return String(value);
  const parts = DISPLAY_FORMATTER.formatToParts(date);
  const get = (type) => parts.find((part) => part.type === type)?.value ?? "";
  const year = get("year");
  return `${get("month")}/${get("day")}/${year.length > 2 ? year.slice(-2) : year} ${get("hour")}:${get("minute")}:${get("second")}`;
}

export function formatDisplayDateOnly(value) {
  if (!value) return "unknown";
  const date = new Date(normalizeIsoDateString(value));
  if (Number.isNaN(date.getTime())) return String(value);
  const parts = DISPLAY_FORMATTER.formatToParts(date);
  const get = (type) => parts.find((part) => part.type === type)?.value ?? "";
  const year = get("year");
  return `${get("month")}/${get("day")}/${year.length > 2 ? year.slice(-2) : year}`;
}
