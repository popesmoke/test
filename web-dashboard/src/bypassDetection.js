import { genericFindingTitle, genericReasonDetail } from "./reviewerCopy.js";

export const BYPASS_TECHNIQUES = [
  {
    id: "process_spoofing",
    label: "Fake program names",
    description: "Renaming suspicious programs to look like trusted software.",
  },
  {
    id: "file_hash_changes",
    label: "Changed file signatures",
    description: "Modified files that no longer match known versions.",
  },
  {
    id: "code_injection",
    label: "Code hidden inside other apps",
    description: "Running suspicious code inside a trusted application.",
  },
  {
    id: "memory_loading",
    label: "Running without a normal install",
    description: "Executing code without leaving a normal installed program.",
  },
  {
    id: "dll_hiding",
    label: "Hidden components",
    description: "Concealing loaded parts of a program from basic inspection.",
  },
  {
    id: "user_mode_api",
    label: "Changed activity logging",
    description: "Turning off or weakening how Windows records program activity.",
  },
  {
    id: "kernel_interference",
    label: "Deep system changes",
    description: "Privileged software trying to hide activity from normal checks.",
  },
  {
    id: "driver_abuse",
    label: "Misused drivers",
    description: "Using drivers to get elevated access to the system.",
  },
  {
    id: "virtualization",
    label: "Virtual machines or emulation",
    description: "Behaving differently when analysis or scanning is detected.",
  },
  {
    id: "scanner_detection",
    label: "Avoiding monitoring tools",
    description: "Changing behavior when monitoring tools are present.",
  },
  {
    id: "memory_obfuscation",
    label: "Hidden memory activity",
    description: "Making memory inspection and signature matching harder.",
  },
  {
    id: "process_hollowing",
    label: "Disguised processes",
    description: "Hosting different code inside a legitimate-looking process.",
  },
  {
    id: "dma_attacks",
    label: "Hardware-assisted access",
    description: "Using hardware to bypass normal system visibility.",
  },
  {
    id: "anticheat_tamper",
    label: "Security software changes",
    description: "Disabling, weakening, or excluding paths from security tools.",
  },
  {
    id: "network_manipulation",
    label: "Network traffic changes",
    description: "Altering client-server traffic instead of local game memory.",
  },
  {
    id: "behavioral_evasion",
    label: "Covering tracks",
    description: "Deleting traces, emptying bins, or cleaning logs after suspicious activity.",
  },
  {
    id: "signature_evasion",
    label: "Hiding deleted programs",
    description: "Deleting or renaming files while traces still remain.",
  },
  {
    id: "containerization",
    label: "Isolated environments",
    description: "Running tools in environments that limit scanner visibility.",
  },
  {
    id: "handle_hiding",
    label: "Hidden system links",
    description: "Hiding relationships between processes and system resources.",
  },
  {
    id: "lolbins",
    label: "Abuse of built-in tools",
    description: "Using trusted Windows tools to clean up or disable logging.",
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
  const title = genericFindingTitle(finding.title);
  const detailSource = finding.action_summary || finding.detail;
  return {
    ...finding,
    techniqueId,
    techniqueLabel: technique.label,
    title,
    whatTheyDid: genericReasonDetail(finding.title, detailSource),
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
