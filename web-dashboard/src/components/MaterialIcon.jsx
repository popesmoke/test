import React from "react";

/** Icons8 CDN — https://icons8.com/icons/all */
const ICON_SLUGS = {
  history: "time-machine",
  document_search: "search-folder",
  speed: "speed",
  warning: "high-priority",
  schedule: "clock",
  sports_esports: "controller",
  forum: "speech-bubble",
  shield: "shield",
  terminal: "console",
  memory: "processor",
  delete: "trash",
  search: "search",
  play_arrow: "play",
  folder_off: "folder-invoices",
  sd_card: "sd-card",
  fingerprint: "fingerprint",
  inventory_2: "box",
  account_tree: "tree-structure",
  add: "plus",
  close: "delete",
  download: "download",
  print: "print",
  menu_book: "open-book",
  description: "document",
  hourglass_top: "hourglass",
  content_copy: "copy",
  admin_panel_settings: "admin-settings-male",
  refresh: "refresh",
  logout: "logout-rounded",
  save: "save",
  delete_sweep: "broom",
  database: "database",
  group: "group",
  lock: "lock",
  track_changes: "goal",
  groups: "group",
  delete_forever: "empty-trash",
  help: "help",
  radar: "radar",
  verified_user: "checked-user-male",
  timer: "timer",
  policy: "privacy",
  dashboard: "control-panel",
  bolt: "lightning-bolt",
  registry: "registry-editor",
  timeline: "timeline",
  hash: "hashtag",
  windows: "windows10",
  certificate: "certificate",
  folder: "folder",
  event_log: "activity-history",
  person: "user-male-circle",
  gpp_maybe: "security-checked",
  play: "play",
  list_checks: "task-planning",
  git_branch: "tree-structure",
  file_code: "source-code",
  file_down: "download",
  users: "group",
  shield_alert: "security-alert",
  alert_triangle: "error",
  help_circle: "help",
  check_circle: "checkmark",
  chevron_right: "chevron-right",
};

export function MaterialIcon({ name, size = 20, className = "", filled = false }) {
  const slug = ICON_SLUGS[name] || name;
  const px = Math.round(size * 1.35);
  const style = filled ? "ios-filled" : "ios-glyphs";
  const src = `https://img.icons8.com/${style}/${px}/9aa3b2/${slug}.png`;
  return (
    <img
      src={src}
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
  const Icon = icon;
  return <Icon size={size} className={className} strokeWidth={1.75} />;
}
