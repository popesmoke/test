import { formatDisplayDate } from "./dateFormat.js";
import { scanReviewFromReport } from "./reportDigest.js";
import {
  buildInvestigationFindings,
  engineVerdictPlain,
  METHODOLOGY_BLURB,
  severityCounts,
} from "./findingsModel.js";
import { privacyPath } from "./resultPrivacy.js";

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

export function findingsToCsv(findings) {
  const header = [
    "id",
    "title",
    "category",
    "severity",
    "confidence",
    "confidence_tier",
    "status",
    "detection_method",
    "location",
    "timestamp",
    "why_flagged",
    "recommended_action",
  ];
  const rows = (findings ?? []).map((f) =>
    [
      f.id,
      f.title,
      f.category,
      f.severity,
      f.confidence ?? "",
      f.confidenceTier,
      f.status,
      f.detectionMethod,
      f.location || "",
      f.timestamp || "",
      f.whyFlagged,
      f.recommendedAction,
    ]
      .map(csvEscape)
      .join(","),
  );
  // UTF-8 BOM helps Excel open severity/confidence columns correctly
  return `\uFEFF${[header.join(","), ...rows].join("\n")}`;
}

export function exportReportPdf({
  detail,
  report,
  summary,
  findings: findingsProp,
  brandName = "Virello Scanner",
}) {
  const pin = detail?.pin ?? "—";
  const completed = detail?.completed_at ? formatDisplayDate(detail.completed_at) : "Pending";
  const findings = findingsProp ?? buildInvestigationFindings(report ?? {}, summary);
  const counts = severityCounts(findings);
  const verdict = engineVerdictPlain(report ?? {}, summary);
  const review = scanReviewFromReport(report ?? {});
  const sec = report?.security_integrity_signals ?? {};
  const env = report?.performance_environment ?? {};
  const scannerVersion =
    report?.scanner_version || report?.client_version || sec?.scanner_version || null;
  const signatureVersion =
    report?.signature_version ||
    sec?.signature_version ||
    sec?.executor_artifact_evidence?.signature_version ||
    null;
  const engineVersion = sec?.evidence_verdict?.engine_version ?? null;

  const findingsHtml = findings.slice(0, 40).map((f) => {
    const evidence = (f.evidence ?? [])
      .slice(0, 4)
      .map((e) => `<li><em>${escapeHtml(e.label)}:</em> ${escapeHtml(e.value)}</li>`)
      .join("");
    return `<article class="finding">
      <header>
        <span class="sev sev-${escapeHtml(f.severity)}">${escapeHtml(f.severity)}</span>
        <span class="conf">${escapeHtml(f.confidenceTier)} confidence</span>
        <span class="status">${escapeHtml(f.status)}</span>
      </header>
      <h3>${escapeHtml(f.title)}</h3>
      <p>${escapeHtml(f.whyFlagged)}</p>
      ${f.location ? `<p class="mono">${escapeHtml(f.location)}</p>` : ""}
      ${evidence ? `<ul class="evidence">${evidence}</ul>` : ""}
      <p class="action"><strong>Action:</strong> ${escapeHtml(f.recommendedAction)}</p>
    </article>`;
  }).join("");

  const envRows = [
    env.os ? ["OS", env.os] : null,
    env.boot_time ? ["Last boot", formatDisplayDate(env.boot_time)] : null,
    report?.generated_at ? ["Scan time", formatDisplayDate(report.generated_at)] : null,
    scannerVersion ? ["Scanner", scannerVersion] : null,
    signatureVersion ? ["Signatures", signatureVersion] : null,
    engineVersion != null ? ["Evidence engine", `v${engineVersion}`] : null,
  ]
    .filter(Boolean)
    .map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(v)}</td></tr>`)
    .join("");

  const chainHtml = (review.evidence_chains?.chains ?? [])
    .slice(0, 8)
    .map((chain) => {
      const steps = (chain.steps ?? [])
        .slice(0, 4)
        .map(
          (step) =>
            `<li>${escapeHtml(step.action || step.source || "trace")} — ${escapeHtml(
              step.detail || privacyPath(step.path) || "Related trace",
            )}</li>`,
        )
        .join("");
      return `<div class="chain"><strong>${escapeHtml(
        (chain.labels ?? []).join(", ") || chain.stem || "Chain",
      )}</strong><p>${escapeHtml(chain.summary || "")}</p><ul>${steps}</ul></div>`;
    })
    .join("");

  const verdictLine = detail?.reviewer_verdict
    ? `<p class="meta">Reviewer verdict: <strong>${escapeHtml(detail.reviewer_verdict)}</strong>${
        detail.reviewer_note ? ` — ${escapeHtml(detail.reviewer_note)}` : ""
      }</p>`
    : "";

  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Investigation ${escapeHtml(pin)}</title>
<style>
  :root { color-scheme: light; }
  body { font-family: "IBM Plex Sans", Arial, sans-serif; margin: 28px; color: #14171c; background: #fff; }
  h1 { font-family: Syne, "IBM Plex Sans", sans-serif; font-size: 22px; margin: 0 0 6px; letter-spacing: -0.02em; }
  h2 { font-size: 13px; margin: 22px 0 10px; border-bottom: 1px solid #2a3038; padding-bottom: 4px; text-transform: uppercase; letter-spacing: 0.08em; }
  h3 { font-size: 14px; margin: 0 0 6px; }
  .meta { color: #4a5560; font-size: 12px; margin: 0 0 8px; }
  .mono { font-family: "IBM Plex Mono", Consolas, monospace; font-size: 11px; word-break: break-all; }
  .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 14px 0; }
  .box { border: 1px solid #2a3038; padding: 10px 12px; border-radius: 2px; }
  .box strong { display: block; font-size: 20px; font-family: "IBM Plex Mono", monospace; }
  .box span { font-size: 11px; color: #4a5560; text-transform: uppercase; letter-spacing: 0.06em; }
  table.env { width: 100%; border-collapse: collapse; font-size: 12px; }
  table.env th { text-align: left; width: 140px; color: #4a5560; padding: 4px 8px 4px 0; font-weight: 500; }
  table.env td { padding: 4px 0; }
  .finding { border: 1px solid #2a3038; border-radius: 2px; padding: 10px 12px; margin: 0 0 10px; page-break-inside: avoid; }
  .finding header { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; font-size: 11px; }
  .sev { text-transform: uppercase; letter-spacing: 0.04em; font-weight: 700; }
  .sev-critical, .sev-high { color: #c43c3c; }
  .sev-medium { color: #8a6a1a; }
  .sev-low { color: #4a5560; }
  .conf, .status { color: #4a5560; }
  .evidence { margin: 6px 0; padding-left: 16px; font-size: 11px; }
  .action { font-size: 11px; color: #2a3038; }
  .chain { border-left: 2px solid #c43c3c; padding: 0 0 0 10px; margin: 0 0 10px; font-size: 12px; }
  .foot { margin-top: 28px; padding-top: 10px; border-top: 1px solid #d0d5db; font-size: 10px; color: #5a6570; line-height: 1.45; }
  @media print { body { margin: 12mm; } .finding { break-inside: avoid; } }
</style></head><body>
  <h1>${escapeHtml(brandName)} — Investigation report</h1>
  <p class="meta">PIN <strong>${escapeHtml(pin)}</strong> · Completed ${escapeHtml(completed)}</p>
  ${verdictLine}
  <p class="meta">Engine verdict: <strong>${escapeHtml(verdict.label)}</strong> — ${escapeHtml(verdict.blurb)}</p>

  <div class="grid">
    <div class="box"><strong>${counts.total}</strong><span>Findings</span></div>
    <div class="box"><strong>${counts.high + counts.critical}</strong><span>High / critical severity</span></div>
    <div class="box"><strong>${counts.confidenceHigh}</strong><span>High confidence</span></div>
  </div>

  <h2>Environment</h2>
  <table class="env">${envRows || "<tr><td>No environment summary available.</td></tr>"}</table>

  <h2>Methodology</h2>
  <p class="meta">${escapeHtml(METHODOLOGY_BLURB)}</p>

  <h2>Findings</h2>
  ${findingsHtml || "<p class='meta'>No investigative findings on this scan.</p>"}

  <h2>Evidence excerpts</h2>
  ${chainHtml || "<p class='meta'>No provenance chains available.</p>"}

  <p class="foot">
    Disclaimer: Findings are investigative indicators intended to assist human review.
    They are not automatic proof of guilt, policy violation, or ban-worthy conduct.
    Severity describes potential impact; confidence describes evidentiary strength — interpret them separately.
    Paths may be privacy-redacted. Full JSON remains available from the dashboard.
  </p>
</body></html>`;

  const frame = document.createElement("iframe");
  frame.style.position = "fixed";
  frame.style.right = "0";
  frame.style.bottom = "0";
  frame.style.width = "0";
  frame.style.height = "0";
  frame.style.border = "0";
  frame.setAttribute("aria-hidden", "true");
  document.body.appendChild(frame);
  const doc = frame.contentDocument || frame.contentWindow?.document;
  if (!doc || !frame.contentWindow) {
    frame.remove();
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `virello-report-${pin}.html`;
    link.click();
    URL.revokeObjectURL(url);
    return;
  }
  doc.open();
  doc.write(html);
  doc.close();
  frame.contentWindow.focus();
  frame.contentWindow.print();
  setTimeout(() => frame.remove(), 1500);
}
