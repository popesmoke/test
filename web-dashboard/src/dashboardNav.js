/** Expert-mode sidebar grouped by reviewer workflow (labels only — icons stay on sections). */
export const EXPERT_NAV_GROUPS = [
  {
    id: "start",
    label: "1 · Overview",
    description: "Verdict, timeline, and recent PC activity.",
    sectionIds: ["starter", "user-activity", "accounts"],
  },
  {
    id: "evidence",
    label: "2 · Findings",
    description: "Deletes, flagged files, cover-up signs, and cross-source proof.",
    sectionIds: ["deletions", "forensic-findings", "forensic-corr", "suspicious", "file-analysis", "bypass"],
  },
  {
    id: "system",
    label: "3 · System",
    description: "OS traces, security, Roblox, and crash logs.",
    sectionIds: ["security", "system", "registry", "memory", "roblox", "crash"],
  },
  {
    id: "raw",
    label: "4 · Deep dive",
    description: "Structured traces for advanced review.",
    sectionIds: ["forensic-artifacts"],
  },
];

export const SIMPLE_TAB_GUIDE = [
  {
    id: "overview",
    step: 1,
    title: "Summary",
    summary: "Verdict, warning signs, and what to read first.",
    searchHint: "Search concern level or problem titles.",
  },
  {
    id: "accounts",
    step: 2,
    title: "Linked accounts",
    summary: "Roblox and Discord accounts found on this device.",
    searchHint: "Search usernames.",
  },
  {
    id: "activity",
    step: 3,
    title: "Activity timeline",
    summary: "Suspicious activity in time order — highest priority first.",
    searchHint: "Try an executor name, deleted, or a file path.",
  },
  {
    id: "downloads",
    step: 4,
    title: "Browser downloads",
    summary: "Files downloaded in Chrome, Edge, Brave, or Firefox.",
    searchHint: "Search .exe names or executor site labels.",
  },
  {
    id: "execution",
    step: 5,
    title: "Programs run",
    summary: "Execution traces from Windows activity logs.",
    searchHint: "Search executor names or .exe paths.",
  },
  {
    id: "programs",
    step: 6,
    title: "Program list",
    summary: "Executables found on disk or recovered after delete.",
    searchHint: "Filter flagged items; Ctrl+F for specific cheats.",
  },
  {
    id: "strings",
    step: 7,
    title: "Keyword matches",
    summary: "Cheat, inject, or cleanup words inside logs and history.",
    searchHint: "Search inject, hub, clear, or executor tokens.",
  },
  {
    id: "security",
    step: 8,
    title: "Security & AV",
    summary: "Defender status, quarantine, PowerShell log, and service changes.",
    searchHint: "Search threat, quarantine, Defender, or service names.",
  },
];
