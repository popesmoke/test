import { genericFindingTitle, genericReasonDetail } from "./reviewerCopy.js";

export const BYPASS_TECHNIQUES = [
  {
    id: "process_spoofing",
    label: "Process name spoofing",
    description: "Renaming or masquerading cheat processes as trusted programs.",
  },
  {
    id: "file_hash_changes",
    label: "File hash changes",
    description: "Modified builds that no longer match known file signatures.",
  },
  {
    id: "code_injection",
    label: "Code injection into legitimate processes",
    description: "Running cheat logic inside a trusted application.",
  },
  {
    id: "memory_loading",
    label: "Reflective or memory-only loading",
    description: "Executing code without leaving a normal installed executable.",
  },
  {
    id: "dll_hiding",
    label: "DLL / module hiding",
    description: "Concealing loaded components from basic inspection.",
  },
  {
    id: "user_mode_api",
    label: "User-mode API manipulation",
    description: "Disabling or weakening Windows logging that records program activity.",
  },
  {
    id: "kernel_interference",
    label: "Kernel-level interference",
    description: "Privileged software trying to hide activity from user-mode scans.",
  },
  {
    id: "driver_abuse",
    label: "Driver abuse",
    description: "Using vulnerable or signed drivers for elevated access.",
  },
  {
    id: "virtualization",
    label: "Virtualization and emulation",
    description: "Behaving differently when analysis or scanning is detected.",
  },
  {
    id: "scanner_detection",
    label: "Debugger and scanner detection",
    description: "Changing behavior when monitoring tools are present.",
  },
  {
    id: "memory_obfuscation",
    label: "Memory protection and obfuscation",
    description: "Making memory inspection and signature matching harder.",
  },
  {
    id: "process_hollowing",
    label: "Process hollowing / masquerading",
    description: "Hosting different code inside a legitimate-looking process.",
  },
  {
    id: "dma_attacks",
    label: "DMA attacks",
    description: "Hardware-assisted access that bypasses normal OS visibility.",
  },
  {
    id: "anticheat_tamper",
    label: "Tampering with the anti-cheat itself",
    description: "Disabling, weakening, or excluding paths from security tools.",
  },
  {
    id: "network_manipulation",
    label: "Network-layer manipulation",
    description: "Altering client-server traffic instead of local game memory.",
  },
  {
    id: "behavioral_evasion",
    label: "Behavioral evasion",
    description: "Deleting traces, emptying bins, or cleaning logs after cheating.",
  },
  {
    id: "signature_evasion",
    label: "Signature evasion",
    description: "Deleting or renaming files while forensic traces remain.",
  },
  {
    id: "containerization",
    label: "Containerization / isolation",
    description: "Running tools in environments that limit scanner visibility.",
  },
  {
    id: "handle_hiding",
    label: "Handle and object hiding",
    description: "Hiding relationships between processes and system resources.",
  },
  {
    id: "lolbins",
    label: "Living-off-the-land techniques",
    description: "Abusing trusted Windows tools to clean up or disable logging.",
  },
];

const TECHNIQUE_BY_ID = Object.fromEntries(BYPASS_TECHNIQUES.map((row) => [row.id, row]));

const TITLE_TECHNIQUE_MAP = [
  ["process_spoofing", /process.*spoof|masquerad/i],
  ["file_hash_changes", /hash|signature|renamed/i],
  ["code_injection", /inject|wmi|persistence|hook/i],
  ["memory_loading", /memory-only|reflective|loader/i],
  ["dll_hiding", /dll|module.*hid/i],
  ["user_mode_api", /prefetch|bam|event log|sysmain|runtime logging|program-run records|amcache|registry/i],
  ["kernel_interference", /kernel|privileged/i],
  ["driver_abuse", /driver|kdmapper|capcom|gdrv/i],
  ["virtualization", /virtual|emulat|sandbox/i],
  ["scanner_detection", /debugger|scanner.*detect|monitoring tool/i],
  ["memory_obfuscation", /obfuscat|protect.*memory/i],
  ["process_hollowing", /hollow|masquerad/i],
  ["dma_attacks", /dma|hardware-assisted/i],
  ["anticheat_tamper", /defender|real-time protection|exclusion|antivirus/i],
  ["network_manipulation", /network|client-server|traffic/i],
  ["behavioral_evasion", /cleanup|recycle|shell history|folder history|shadow-copy|deleted|removed|ghost|traces line up/i],
  ["signature_evasion", /prefetch proves|forensic traces after deletion|deleted executor|deleted cheat|missing safety markers/i],
  ["containerization", /container|isolation|vm/i],
  ["handle_hiding", /handle|object hid|wmi/i],
  ["lolbins", /wevtutil|powershell|cipher|vssadmin|fsutil/i],
];

const CATEGORY_TECHNIQUE_MAP = {
  tamper: "user_mode_api",
  cover_up: "behavioral_evasion",
  defender: "anticheat_tamper",
  ghost_trace: "signature_evasion",
  persistence: "code_injection",
  correlation: "behavioral_evasion",
};

export function inferBypassTechnique(finding) {
  if (finding?.technique && TECHNIQUE_BY_ID[finding.technique]) {
    return finding.technique;
  }
  const blob = `${finding?.title || ""} ${finding?.detail || ""} ${finding?.category || ""}`;
  for (const [techniqueId, pattern] of TITLE_TECHNIQUE_MAP) {
    if (pattern.test(blob)) return techniqueId;
  }
  return CATEGORY_TECHNIQUE_MAP[finding?.category] || "behavioral_evasion";
}

export function techniqueMeta(techniqueId) {
  return TECHNIQUE_BY_ID[techniqueId] || TECHNIQUE_BY_ID.behavioral_evasion;
}

export function normalizeBypassFinding(finding) {
  const techniqueId = inferBypassTechnique(finding);
  const technique = techniqueMeta(techniqueId);
  return {
    ...finding,
    techniqueId,
    techniqueLabel: technique.label,
    title: genericFindingTitle(finding.title),
    whatTheyDid: finding.action_summary || genericReasonDetail(finding.title, finding.detail),
    detail: genericReasonDetail(finding.title, finding.detail),
  };
}

export function buildBypassReport(bypass) {
  const rawFindings = bypass?.findings ?? [];
  const findings = rawFindings.map(normalizeBypassFinding);
  const byTechnique = new Map();

  for (const row of findings) {
    const bucket = byTechnique.get(row.techniqueId) ?? [];
    bucket.push(row);
    byTechnique.set(row.techniqueId, bucket);
  }

  const detected = [...byTechnique.entries()]
    .map(([techniqueId, items]) => ({
      techniqueId,
      technique: techniqueMeta(techniqueId),
      findings: items.sort((a, b) => severityRank(b.severity) - severityRank(a.severity)),
    }))
    .sort((a, b) => {
      const aMax = Math.max(...a.findings.map((row) => severityRank(row.severity)));
      const bMax = Math.max(...b.findings.map((row) => severityRank(row.severity)));
      return bMax - aMax;
    });

  const detectedIds = new Set(detected.map((row) => row.techniqueId));
  const monitored = BYPASS_TECHNIQUES.filter((row) => !detectedIds.has(row.id));

  return {
    available: Boolean(bypass?.available ?? rawFindings.length),
    riskScore: bypass?.risk_score ?? 0,
    riskLevel: bypass?.risk_level || "low",
    findingCount: findings.length,
    detected,
    monitored,
    findings,
  };
}

function severityRank(severity) {
  return { critical: 4, high: 3, medium: 2, low: 1 }[severity] || 0;
}
