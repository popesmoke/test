import { formatDisplayDate } from "./dateFormat.js";
import { scanReviewFromReport } from "./reportDigest.js";

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function exportReportPdf({ detail, report, summary, brandName = "Virello Scanner" }) {
  const pin = detail?.pin ?? "—";
  const completed = detail?.completed_at ? formatDisplayDate(detail.completed_at) : "Pending";
  const score = summary?.score ?? 0;
  const reasons = (summary?.reasons ?? []).filter((r) => r.points > 0).slice(0, 8);
  const problems = reasons.map((r) => `<li><strong>${escapeHtml(r.label)}</strong> — ${escapeHtml(r.detail)}</li>`).join("");
  const review = scanReviewFromReport(report ?? {});
  const deletions = (review.last_computer_activity?.events ?? [])
    .filter((e) => e.category === "deletions" || String(e.summary || "").includes("no longer on disk"))
    .slice(0, 6)
    .map((e) => {
      const when = e.occurred_at ? formatDisplayDate(e.occurred_at) : "Time unknown";
      return `<li>${escapeHtml(when)} — ${escapeHtml(e.summary || e.path || e.label)}</li>`;
    })
    .join("");
  const verdictLine = detail?.reviewer_verdict
    ? `<p class="meta">Reviewer verdict: <strong>${escapeHtml(detail.reviewer_verdict)}</strong>${detail.reviewer_note ? ` — ${escapeHtml(detail.reviewer_note)}` : ""}</p>`
    : "";

  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Scan ${escapeHtml(pin)}</title>
<style>
  body { font-family: Arial, sans-serif; margin: 24px; color: #111; }
  h1 { font-size: 20px; margin: 0 0 8px; }
  .meta { color: #444; font-size: 13px; margin-bottom: 16px; }
  .score { font-size: 28px; font-weight: bold; margin: 12px 0; }
  h2 { font-size: 14px; margin: 18px 0 8px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
  ul { margin: 0; padding-left: 18px; font-size: 12px; line-height: 1.45; }
  .foot { margin-top: 24px; font-size: 11px; color: #666; }
  @media print { body { margin: 12mm; } }
</style></head><body>
  <h1>${escapeHtml(brandName)} — scan summary</h1>
  <p class="meta">PIN <strong>${escapeHtml(pin)}</strong> · Completed ${escapeHtml(completed)}</p>
  ${verdictLine}
  <div class="score">Suspicion score: ${score}/100</div>
  <h2>Top findings</h2>
  <ul>${problems || "<li>No scored warning signs on this scan.</li>"}</ul>
  <h2>Recent deletions (if any)</h2>
  <ul>${deletions || "<li>No timestamped deletion events.</li>"}</ul>
  <p class="foot">One-page summary for admin review. Full JSON is available from the dashboard download button.</p>
</body></html>`;

  const frame = document.createElement("iframe");
  frame.style.position = "fixed";
  frame.style.right = "0";
  frame.style.bottom = "0";
  frame.style.width = "0";
  frame.style.height = "0";
  frame.style.border = "0";
  document.body.appendChild(frame);
  const doc = frame.contentDocument || frame.contentWindow.document;
  doc.open();
  doc.write(html);
  doc.close();
  frame.contentWindow.focus();
  frame.contentWindow.print();
  setTimeout(() => frame.remove(), 1000);
}
