/** Expert-mode sidebar grouped by reviewer workflow (labels only — icons stay on sections). */
export const EXPERT_NAV_GROUPS = [
  {
    id: "start",
    label: "1 · Start here",
    description: "Score, timeline, and what happened on the PC.",
    sectionIds: ["starter", "user-activity"],
  },
  {
    id: "evidence",
    label: "2 · Evidence",
    description: "Deletes, files, bypass signals, and cross-source proof.",
    sectionIds: ["deletions", "forensic-findings", "forensic-corr", "suspicious", "file-analysis", "bypass"],
  },
  {
    id: "system",
    label: "3 · System & apps",
    description: "OS traces, registry, memory, Roblox, and crashes.",
    sectionIds: ["system", "registry", "memory", "roblox", "crash"],
  },
  {
    id: "raw",
    label: "4 · Raw traces",
    description: "Structured JSON samples for deep review.",
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
    id: "activity",
    step: 2,
    title: "Last activity",
    summary: "Deletes, runs, and downloads in time order (MM/DD/YY).",
    searchHint: "Try Potassium, deleted, Recycle Bin, or a file path.",
  },
  {
    id: "downloads",
    step: 3,
    title: "Download history",
    summary: "Browser downloads — same list Chrome/Edge would show.",
    searchHint: "Search .exe names or executor labels.",
  },
  {
    id: "execution",
    step: 4,
    title: "Programs run",
    summary: "Execution traces (BAM, Prefetch, etc.).",
    searchHint: "Search executor names or .exe paths.",
  },
  {
    id: "programs",
    step: 5,
    title: "Program list",
    summary: "Executables found on disk or recovered after delete.",
    searchHint: "Filter flagged items; Ctrl+F for specific cheats.",
  },
  {
    id: "strings",
    step: 6,
    title: "Word matches",
    summary: "Cheat/inject/cleanup words inside logs and history.",
    searchHint: "Search inject, hub, clear, or executor tokens.",
  },
];
