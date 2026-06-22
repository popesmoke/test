import React from "react";
import { Link } from "react-router-dom";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { IconDiscord } from "../components/VirelloIcons.jsx";

const FEATURES = [
  {
    icon: "search",
    title: "Execution timeline",
    text: "See what ran on the PC and when — sorted by risk so reviewers open the worst hits first.",
    wide: true,
  },
  {
    icon: "download",
    title: "Download history",
    text: "Browser downloads cross-checked against known executor names and suspicious file labels.",
  },
  {
    icon: "hash",
    title: "Renamed binary detection",
    text: "Fingerprints catch executors even when the file on disk was renamed or moved.",
  },
  {
    icon: "folder",
    title: "Profile folder sweep",
    text: "Downloads, Desktop, and Documents scanned for cheat loaders and disguised filenames.",
  },
  {
    icon: "group",
    title: "Linked account correlation",
    text: "Roblox and Discord accounts found on the device, shown together for context.",
  },
  {
    icon: "speed",
    title: "Risk scoring engine",
    text: "Findings ranked by severity. Weak signals stay buried unless they stack with stronger ones.",
  },
  {
    icon: "lock",
    title: "Consent-first collection",
    text: "The user approves the scan before anything leaves their PC. No passwords or messages.",
  },
  {
    icon: "dashboard",
    title: "Case review dashboard",
    text: "PIN-based handoff from scanner to reviewer. Notes, verdicts, and export in one place.",
  },
];

export function LandingPage() {
  return (
    <div className="landing">
      <section className="hero hero--asymmetric">
        <div className="hero__content">
          <p className="hero__eyebrow">Windows · Roblox · Screenshare</p>
          <h1>Detect Roblox executors in minutes</h1>
          <p className="hero__lead">
            Built for Discord screenshare reviews. Virello scans a Windows PC with the user&apos;s consent,
            ranks what it finds, and hands reviewers a structured case — not a wall of raw logs.
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
            <li>29 executor brands on the watch list</li>
            <li>Typical scan under 3 minutes</li>
          </ul>
        </div>
        <aside className="hero__panel">
          <div className="hero__panel-inner">
            <div className="hero__stat hero__stat--highlight">
              <MaterialIcon name="timer" size={22} />
              <span className="hero__stat-value">~3 min</span>
              <span className="hero__stat-label">Typical scan time on a standard gaming PC</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">29</span>
              <span className="hero__stat-label">Executor brands tracked (Volt, Wave, Solara, Xeno, …)</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">Win 10+</span>
              <span className="hero__stat-label">Desktop scanner — Windows 10 and 11</span>
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
          <h2>Evidence-based executor detection for Roblox moderation</h2>
          <p>
            Each capability maps to a real section in the review console — not marketing filler.
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

      <p className="landing-attribution muted">
        Icons by{" "}
        <a href="https://icons8.com" target="_blank" rel="noreferrer">
          Icons8
        </a>
      </p>
    </div>
  );
}
