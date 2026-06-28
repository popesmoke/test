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

export function formatRelativeMinutesAgo(value, referenceMs = Date.now()) {
  if (value == null || value === "") return null;
  const date = new Date(normalizeIsoDateString(value));
  if (Number.isNaN(date.getTime())) return null;
  const minutes = Math.max(0, Math.floor((referenceMs - date.getTime()) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes === 1) return "1 minute ago";
  if (minutes < 60) return `${minutes} minutes ago`;
  const hours = Math.floor(minutes / 60);
  if (hours === 1) return "1 hour ago";
  if (hours < 24) return `${hours} hours ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "1 day ago" : `${days} days ago`;
}

export function formatMinutesAgoLabel(minutes) {
  if (minutes == null || Number.isNaN(Number(minutes))) return null;
  const value = Math.max(0, Math.floor(Number(minutes)));
  if (value < 1) return "just now";
  if (value === 1) return "1 minute ago";
  if (value < 60) return `${value} minutes ago`;
  const hours = Math.floor(value / 60);
  if (hours === 1) return "1 hour ago";
  if (hours < 24) return `${hours} hours ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "1 day ago" : `${days} days ago`;
}
