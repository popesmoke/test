/** Reviewer workspace navigation guide (streamlined single workflow). */
export const SIMPLE_TAB_GUIDE = [
  {
    id: "summary",
    step: 1,
    title: "Summary",
    summary: "Overall assessment and the most important concerns.",
    searchHint: "Check the concern level and top warning signs.",
  },
  {
    id: "findings",
    step: 2,
    title: "Findings",
    summary: "All warning signs, linked traces, and flagged programs.",
    searchHint: "Review items sorted by importance.",
  },
  {
    id: "traces",
    step: 3,
    title: "Traces",
    summary: "Which Windows data layers were checked and any cross-check mismatches.",
    searchHint: "See Defender, Prefetch, BAM, SRUM, USN, and other trace sources.",
  },
  {
    id: "security",
    step: 4,
    title: "Security",
    summary: "Defender history, exclusions, log clearing, and trace-cleaner signals.",
    searchHint: "Look for disabled protection, exclusions, or cleanup activity.",
  },
  {
    id: "activity",
    step: 5,
    title: "Activity",
    summary: "Timeline, downloads, programs that ran, and deletions.",
    searchHint: "Look for suspicious downloads, program runs, or file removals.",
  },
  {
    id: "accounts",
    step: 6,
    title: "Accounts",
    summary: "Roblox and Discord accounts found on this device.",
    searchHint: "Check linked game and chat accounts.",
  },
];

/** @deprecated Expert mode removed — kept for tutorial compatibility. */
export const EXPERT_NAV_GROUPS = [];
