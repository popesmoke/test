import React, { useEffect, useState } from "react";
import { Save } from "lucide-react";

const VERDICTS = [
  { id: "", label: "No verdict" },
  { id: "cleared", label: "Cleared" },
  { id: "suspicious", label: "Suspicious" },
  { id: "ban", label: "Ban" },
  { id: "follow-up", label: "Follow-up" },
];

export function SessionReview({ detail, apiUrl, token, authHeaders, onSaved }) {
  const [verdict, setVerdict] = useState(detail?.reviewer_verdict ?? "");
  const [note, setNote] = useState(detail?.reviewer_note ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setVerdict(detail?.reviewer_verdict ?? "");
    setNote(detail?.reviewer_note ?? "");
    setMessage("");
  }, [detail?.id, detail?.reviewer_verdict, detail?.reviewer_note]);

  if (!detail || detail.status !== "completed") return null;

  async function saveReview() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${apiUrl}/sessions/${detail.id}/review`, {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ verdict, note }),
      });
      if (!response.ok) throw new Error(`Save failed: ${response.status}`);
      const data = await response.json();
      onSaved?.(data);
      setMessage("Saved.");
    } catch (caught) {
      setMessage(caught.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="session-review">
      <div className="session-review-head">
        <h3>Session verdict</h3>
        <p className="muted">Private reviewer tags for PIN {detail.pin}.</p>
      </div>
      <div className="session-review-grid">
        <label>
          Verdict
          <select value={verdict} onChange={(e) => setVerdict(e.target.value)}>
            {VERDICTS.map((item) => (
              <option key={item.id || "none"} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="session-review-note">
          Note
          <textarea
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Staff-only note for this scan…"
          />
        </label>
      </div>
      <div className="session-review-actions">
        <button type="button" className="primary" onClick={saveReview} disabled={busy}>
          <Save size={15} /> {busy ? "Saving…" : "Save review"}
        </button>
        {message ? <span className="muted">{message}</span> : null}
      </div>
    </section>
  );
}
