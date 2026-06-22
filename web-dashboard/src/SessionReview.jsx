import React, { useEffect, useState } from "react";
import { MaterialIcon } from "./components/MaterialIcon.jsx";

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
    <section className="session-review session-review--inline">
      <label className="session-review__field">
        <span>Verdict</span>
        <select value={verdict} onChange={(e) => setVerdict(e.target.value)}>
          {VERDICTS.map((item) => (
            <option key={item.id || "none"} value={item.id}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <label className="session-review__field session-review__field--grow">
        <span>Reviewer note</span>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Private note for this case…"
        />
      </label>
      <button type="button" className="btn btn--primary btn--sm session-review__save" onClick={saveReview} disabled={busy}>
        <MaterialIcon name="save" size={15} /> {busy ? "Saving…" : "Save"}
      </button>
      {message ? <span className="session-review__msg">{message}</span> : null}
    </section>
  );
}
