import React, { useMemo } from "react";
import { MaterialIcon } from "./MaterialIcon.jsx";
import { SeverityBadge } from "./SeverityBadge.jsx";
import { buildBypassReport } from "../bypassDetection.js";

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

function BypassFindingRow({ finding }) {
  return (
    <article className={`ws-bypass-finding ws-bypass-finding--${finding.severity || "medium"}`}>
      <div className="ws-bypass-finding__head">
        <div>
          <strong>{finding.title}</strong>
          <p className="muted">{finding.techniqueLabel}</p>
        </div>
        <SeverityBadge severity={finding.severity || "medium"} compact showIcon={false} />
      </div>
      <p className="ws-bypass-action">
        <span className="ws-bypass-action__label">What happened</span>
        {finding.whatTheyDid}
      </p>
    </article>
  );
}

export function BypassPanel({ report }) {
  const bypass = report?.security_integrity_signals?.bypass_resilience ?? {};
  const view = useMemo(() => buildBypassReport(bypass), [bypass]);

  const riskTone =
    view.riskLevel === "high" ? "bad" : view.riskLevel === "medium" ? "watch" : "clean";

  return (
    <>
      <section className={`ws-bypass-hero ws-bypass-hero--${riskTone}`}>
        <div>
          <p className="ws-bypass-hero__label">Hiding activity</p>
          <h3>{view.findingCount ? "Signs of hiding activity found" : "No hiding activity detected"}</h3>
          <p className="muted">
            {view.findingCount
              ? `${view.findingCount} concern${view.findingCount === 1 ? "" : "s"} found across ${view.detected.length} area${view.detected.length === 1 ? "" : "s"}.`
              : "Nothing suggested that someone tried to hide or clean up suspicious activity."}
          </p>
        </div>
        <div className="ws-bypass-hero__meter" aria-label={`Concern level ${view.riskScore} out of 100`}>
          <strong>{view.riskScore}</strong>
          <span>concern level</span>
        </div>
      </section>

      {view.detected.length ? (
        <section className="ws-panel">
          <PanelHeader
            icon="shield_alert"
            title="Detected hiding activity"
            text="Each item explains what looked unusual in plain language."
          />
          <div className="ws-panel__body">
            {view.detected.map((group) => (
              <div key={group.techniqueId} className="ws-bypass-group">
                <header className="ws-bypass-group__head">
                  <MaterialIcon name="security" size={18} />
                  <div>
                    <strong>{group.technique.label}</strong>
                    <p className="muted">{group.technique.description}</p>
                  </div>
                  <span className="ws-bypass-group__count">
                    {group.findings.length} item{group.findings.length === 1 ? "" : "s"}
                  </span>
                </header>
                <div className="ws-bypass-finding-list">
                  {group.findings.map((finding, index) => (
                    <BypassFindingRow key={`${finding.title}-${index}`} finding={finding} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : (
        <div className="ws-empty-state">
          <MaterialIcon name="verified_user" size={28} />
          <p>No signs of log wiping, security changes, or trace cleanup on this scan.</p>
        </div>
      )}
    </>
  );
}
