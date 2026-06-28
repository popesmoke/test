import React, { useMemo } from "react";
import { MaterialIcon } from "./MaterialIcon.jsx";
import { SeverityBadge } from "./SeverityBadge.jsx";
import { formatMinutesAgoLabel, formatRelativeMinutesAgo } from "../dateFormat.js";

function PanelHeader({ icon, title, text }) {
  return (
    <header className="ws-panel__head">
      <MaterialIcon name={icon} size={20} />
      <div>
        <h4>{title}</h4>
        {text ? <p>{text}</p> : null}
      </div>
    </header>
  );
}

const SOURCE_LABELS = {
  recycle_bin: "Recycle bin",
  prefetch: "Prefetch",
  usn_journal: "USN journal",
  bam: "BAM",
  deletion_signals: "Deletion signals",
  tamper: "Tamper",
  cover_up: "Cover-up",
  event_log: "Event log",
  volume_shadow_copy: "Shadow copies",
};

export function ForensicTimelinePanel({ report, formatGmtPlus3 }) {
  const timeline = report?.security_integrity_signals?.forensic_timeline ?? {};
  const generatedAt = report?.generated_at;
  const referenceMs = generatedAt ? new Date(generatedAt).getTime() : Date.now();

  const recycleLabel = useMemo(() => {
    if (timeline.recycle_bin_latest_change_minutes_ago != null) {
      return formatMinutesAgoLabel(timeline.recycle_bin_latest_change_minutes_ago);
    }
    return formatRelativeMinutesAgo(timeline.recycle_bin_latest_at, referenceMs);
  }, [timeline, referenceMs]);

  const events = timeline.events ?? [];

  if (!timeline.available && !recycleLabel && !events.length) {
    return null;
  }

  return (
    <section className="ws-panel">
      <PanelHeader
        icon="timeline"
        title="Evidence changes"
        text={
          recycleLabel
            ? `Recycle bin last changed ${recycleLabel}.`
            : "Recent changes across prefetch, USN, BAM, and recycle bin."
        }
      />
      <div className="ws-panel__body">
        {events.length ? (
          <ul className="ws-activity-list">
            {events.map((event, index) => {
              const relative =
                event.minutes_ago != null
                  ? formatMinutesAgoLabel(event.minutes_ago)
                  : formatRelativeMinutesAgo(event.occurred_at, referenceMs);
              const sourceLabel = SOURCE_LABELS[event.source] || event.source || "Evidence";
              return (
                <li key={`${event.source}-${event.change}-${index}`} className="ws-activity-card">
                  <time className="ws-activity-card__time">
                    {relative || (event.occurred_at ? formatGmtPlus3(event.occurred_at) : "Unknown")}
                  </time>
                  <div className="ws-activity-card__body">
                    <div className="ws-static-finding__head">
                      <SeverityBadge severity={event.severity === "info" ? "low" : (event.severity || "medium")} compact showIcon={false} />
                      <strong>{sourceLabel}</strong>
                    </div>
                    <p className="ws-activity-card__title">{event.change}</p>
                    {event.detail ? <p className="ws-activity-card__meta muted">{event.detail}</p> : null}
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="muted">No prefetch, USN, BAM, or recycle bin changes were flagged on this scan.</p>
        )}
      </div>
    </section>
  );
}
