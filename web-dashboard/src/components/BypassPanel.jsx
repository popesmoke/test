import React, { useMemo, useState } from "react";
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

function BypassFindingCard({ finding, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <article className={`ws-collapse-card ws-collapse-card--${finding.severity || "medium"} ${open ? "is-open" : ""}`}>
      <button type="button" className="ws-collapse-card__trigger" onClick={() => setOpen((v) => !v)}>
        <span className="ws-collapse-card__icon" aria-hidden>
          <MaterialIcon name="gpp_maybe" size={18} />
        </span>
        <span className="ws-collapse-card__text">
          <strong>{finding.title}</strong>
          <span className="ws-collapse-card__sub">{finding.techniqueLabel}</span>
        </span>
        <SeverityBadge severity={finding.severity || "medium"} compact />
        <MaterialIcon name="expand_more" size={20} className="ws-collapse-card__chevron" />
      </button>
      {open ? (
        <div className="ws-collapse-card__content">
          <p className="ws-bypass-action">
            <span className="ws-bypass-action__label">What they did</span>
            {finding.whatTheyDid}
          </p>
          {finding.detail && finding.detail !== finding.whatTheyDid ? (
            <p className="muted">{finding.detail}</p>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

export function BypassPanel({ report }) {
  const bypass = report?.security_integrity_signals?.bypass_resilience ?? {};
  const view = useMemo(() => buildBypassReport(bypass), [bypass]);
  const [showMonitored, setShowMonitored] = useState(false);

  const riskTone =
    view.riskLevel === "high" ? "bad" : view.riskLevel === "medium" ? "watch" : "clean";

  return (
    <>
      <section className={`ws-bypass-hero ws-bypass-hero--${riskTone}`}>
        <div>
          <p className="ws-bypass-hero__label">Bypass detection</p>
          <h3>{view.findingCount ? "Suspicious hiding activity found" : "No bypass attempts detected"}</h3>
          <p className="muted">
            {view.findingCount
              ? `${view.findingCount} signal${view.findingCount === 1 ? "" : "s"} across ${view.detected.length} technique${view.detected.length === 1 ? "" : "s"}.`
              : "Windows logging, Defender, shell history, and forensic traces all looked normal."}
          </p>
        </div>
        <div className="ws-bypass-hero__meter" aria-label={`Bypass risk ${view.riskScore} out of 100`}>
          <strong>{view.riskScore}</strong>
          <span>bypass risk</span>
        </div>
      </section>

      {view.detected.length ? (
        <section className="ws-panel">
          <PanelHeader
            icon="shield_alert"
            title="Detected bypass activity"
            text="Each item explains what was done and which evasion category it matches."
          />
          <div className="ws-panel__body ws-collapse-stack">
            {view.detected.map((group) => (
              <div key={group.techniqueId} className="ws-bypass-group">
                <header className="ws-bypass-group__head">
                  <MaterialIcon name="security" size={18} />
                  <div>
                    <strong>{group.technique.label}</strong>
                    <p className="muted">{group.technique.description}</p>
                  </div>
                  <span className="ws-bypass-group__count">
                    {group.findings.length} hit{group.findings.length === 1 ? "" : "s"}
                  </span>
                </header>
                <div className="ws-collapse-stack">
                  {group.findings.map((finding, index) => (
                    <BypassFindingCard key={`${finding.title}-${index}`} finding={finding} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : (
        <div className="ws-empty-state">
          <MaterialIcon name="verified_user" size={28} />
          <p>No signs of log wiping, Defender tampering, or trace cleanup on this scan.</p>
        </div>
      )}

      <section className="ws-panel ws-panel--compact">
        <button type="button" className="ws-bypass-monitored-toggle" onClick={() => setShowMonitored((v) => !v)}>
          <MaterialIcon name={showMonitored ? "expand_less" : "expand_more"} size={18} />
          <span>
            {showMonitored ? "Hide" : "Show"} monitored bypass techniques ({BYPASS_TECHNIQUES.length})
          </span>
        </button>
        {showMonitored ? (
          <ul className="ws-bypass-monitored-list">
            {view.monitored.map((technique) => (
              <li key={technique.id}>
                <strong>{technique.label}</strong>
                <span className="muted">{technique.description}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </>
  );
}

import { buildBypassReport, BYPASS_TECHNIQUES } from "../bypassDetection.js";
