import React from "react";

/** Icons8 Windows style slugs — https://icons8.com/icons */
const ICONS8_SLUGS = {
  history: "activity-history",
  document_search: "search",
  speed: "speedometer",
  warning: "warning-shield",
  schedule: "clock",
  sports_esports: "controller",
  forum: "chat",
  shield: "shield",
  terminal: "console",
  memory: "chip",
  delete: "trash",
  search: "search",
  play_arrow: "play",
  folder_off: "folder-invoices",
  sd_card: "chip",
  fingerprint: "fingerprint",
  inventory_2: "box",
  account_tree: "tree-structure",
  add: "plus",
  close: "delete-sign",
  download: "download",
  print: "print",
  menu_book: "book",
  description: "document",
  hourglass_top: "hourglass",
  content_copy: "copy",
  admin_panel_settings: "admin-settings-male",
  refresh: "refresh",
  logout: "logout-rounded",
  delete_sweep: "broom",
  database: "database",
  group: "groups",
  lock: "lock",
  track_changes: "goal",
  groups: "conference-call",
  delete_forever: "trash",
  help: "help",
  radar: "radar",
  verified_user: "verified-account",
  timer: "timer",
  policy: "privacy",
  dashboard: "dashboard",
  bolt: "lightning-bolt",
  registry: "registry-editor",
  timeline: "timeline",
  hash: "hashtag",
  windows: "windows-10",
  certificate: "certificate",
  folder: "folder-invoices",
  event_log: "log",
  person: "user-male-circle",
  gpp_maybe: "privacy",
  play: "play",
  list_checks: "checklist",
  git_branch: "link",
  file_code: "source-code",
  file_down: "download-from-cloud",
  users: "conference-call",
  shield_alert: "high-importance",
  alert_triangle: "warning-shield",
  help_circle: "help",
  check_circle: "checkmark",
  chevron_right: "forward",
  play_circle: "play",
  recent_actors: "clock",
  recycle_bin: "trash",
  security: "shield",
  file_search: "search",
  expand_more: "expand-arrow",
  expand_less: "collapse-arrow",
  priority_high: "high-priority",
  alert_circle: "error",
  info: "info",
};

function icons8Url(slug, size) {
  return `https://img.icons8.com/ios-glyphs/${size}/ffffff/${slug}.png`;
}

export function MaterialIcon({ name, size = 20, className = "" }) {
  const slug = ICONS8_SLUGS[name];
  if (!slug) {
    return (
      <span
        className={`icons8-icon icons8-icon--fallback ${className}`.trim()}
        style={{
          display: "inline-flex",
          width: size,
          height: size,
          alignItems: "center",
          justifyContent: "center",
          verticalAlign: "middle",
          flexShrink: 0,
          fontSize: Math.max(10, size - 6),
          fontWeight: 700,
          opacity: 0.55,
        }}
        aria-hidden="true"
      >
        ?
      </span>
    );
  }
  return (
    <img
      src={icons8Url(slug, size)}
      alt=""
      width={size}
      height={size}
      className={`icons8-icon ${className}`.trim()}
      loading="lazy"
      decoding="async"
      aria-hidden="true"
      style={{ display: "inline-block", verticalAlign: "middle", flexShrink: 0 }}
    />
  );
}

export function renderIcon(icon, size = 20, className = "") {
  if (!icon) return null;
  if (typeof icon === "string") {
    return <MaterialIcon name={icon} size={size} className={className} />;
  }
  return <MaterialIcon name="help" size={size} className={className} />;
}
