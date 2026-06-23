import React from "react";
import { Link } from "react-router-dom";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { IconDiscord } from "../components/VirelloIcons.jsx";

const FEATURES = [
  {
    icon: "search",
    title: "Activity timeline",
    text: "Recent PC activity in order. The strongest signals rise to the top.",
    wide: true,
  },
  {
    icon: "download",
    title: "Download history",
    text: "Browser downloads checked against your review rules.",
  },
  {
    icon: "hash",
    title: "File fingerprinting",
    text: "Known signatures still match after renames or folder moves.",
  },
  {
    icon: "folder",
    title: "Profile folder scan",
    text: "Common user folders checked against your watch lists.",
  },
  {
    icon: "group",
    title: "Linked accounts",
    text: "Game and chat accounts on the device, grouped for context.",
  },
  {
    icon: "speed",
    title: "Priority scoring",
    text: "Findings ranked so reviewers see what matters first.",
  },
  {
    icon: "lock",
    title: "Consent-first collection",
    text: "Nothing leaves the PC until the user approves. No passwords or private messages.",
  },
  {
    icon: "dashboard",
    title: "Review workspace",
    text: "PIN handoff, reviewer notes, verdicts, and export in one console.",
  },
];

export function LandingPage() {
  return (
    <div className="landing">
      <section className="hero hero--asymmetric">
        <div className="hero__content">
          <p className="hero__eyebrow">Windows · Screenshare reviews</p>
          <h1>Structured PC scans for live reviews</h1>
          <p className="hero__lead">
            Virello collects system signals with the user&apos;s consent, ranks what matters,
            and hands reviewers a clear case file, not a wall of raw logs.
          </p>
          <div className="hero__actions">
            <Link to="/download" className="btn btn--primary btn--lg">
              Download scanner
            </Link>
            <Link to="/workspace" className="btn btn--outline btn--lg">
              Open review console
            </Link>
            <a className="btn btn--ghost btn--lg" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
              <IconDiscord size={18} />
              Discord
            </a>
          </div>
          <ul className="hero__trust">
            <li>User must approve before upload</li>
            <li>Configurable watch lists</li>
            <li>Most scans finish in about 2 minutes</li>
          </ul>
        </div>
        <aside className="hero__panel">
          <div className="hero__panel-inner">
            <div className="hero__stat hero__stat--highlight">
              <MaterialIcon name="timer" size={22} />
              <span className="hero__stat-value">~2 min</span>
              <span className="hero__stat-label">Typical scan time on a modern gaming PC</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">Multi</span>
              <span className="hero__stat-label">Signal layers across files, logs, registry, and runtime</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">Win 10+</span>
              <span className="hero__stat-label">Desktop scanner for Windows 10 and 11</span>
            </div>
            <div className="hero__stat hero__stat--muted">
              <span className="hero__stat-value">PIN</span>
              <span className="hero__stat-label">One-time session code links scan to reviewer</span>
            </div>
          </div>
          <p className="hero__panel-note muted">
            Reviewers sign in with Discord. Scanned users never need an account.
          </p>
        </aside>
      </section>

      <section className="section">
        <header className="section__header section__header--left">
          <p className="section__eyebrow">What you get</p>
          <h2>Built for reviewers who need signal, not noise</h2>
          <p>
            Each capability maps to a real section in the review console.
          </p>
        </header>
        <div className="feature-grid feature-grid--asymmetric">
          {FEATURES.map((feature) => (
            <article
              key={feature.title}
              className={`feature-card${feature.wide ? " feature-card--wide" : ""}`}
            >
              <div className="feature-card__icon">
                <MaterialIcon name={feature.icon} size={22} />
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="cta-band">
        <div>
          <h2>Run a scan. Review the case.</h2>
          <p>Download the Windows scanner, generate a PIN in the console, and share it during screenshare.</p>
        </div>
        <div className="cta-band__actions">
          <Link to="/download" className="btn btn--primary">
            Download
          </Link>
          <Link to="/workspace" className="btn btn--outline">
            Console
          </Link>
        </div>
      </section>

    </div>
  );
}
