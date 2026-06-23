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
    description: "Extra detail for experienced reviewers.",
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
    summary: "Suspicious activity in time order, highest priority first.",
    searchHint: "Search program names, deleted, or file paths.",
  },
  {
    id: "downloads",
    step: 4,
    title: "Downloads",
    summary: "Files downloaded in common browsers.",
    searchHint: "Search file names or site labels.",
  },
  {
    id: "execution",
    step: 5,
    title: "Programs run",
    summary: "Programs that ran recently on this PC.",
    searchHint: "Search program names or file paths.",
  },
  {
    id: "programs",
    step: 6,
    title: "Program list",
    summary: "Programs found on disk or still logged after delete.",
    searchHint: "Filter flagged items or search for a name.",
  },
  {
    id: "strings",
    step: 7,
    title: "Keyword matches",
    summary: "Watch-list words found in logs and history.",
    searchHint: "Search keywords from your watch lists.",
  },
  {
    id: "security",
    step: 8,
    title: "Security & AV",
    summary: "Defender status, quarantine, PowerShell log, and service changes.",
    searchHint: "Search threat, quarantine, Defender, or service names.",
  },
];
