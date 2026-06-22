import React from "react";
import { Link } from "react-router-dom";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { IconDiscord } from "../components/VirelloIcons.jsx";

const FEATURES = [
  {
    icon: "radar",
    title: "Deep forensic scanning",
    text: "Execution traces, filesystem artifacts, Roblox runtime signals, and correlated findings in one pass.",
  },
  {
    icon: "verified_user",
    title: "Fewer false positives",
    text: "Evidence is scored by reliability. Weak signals need backup before they affect a verdict.",
  },
  {
    icon: "timer",
    title: "Fast, bounded scans",
    text: "Primary results arrive within six minutes. Background collectors finish without blocking the report.",
  },
  {
    icon: "policy",
    title: "Consent first design",
    text: "Users approve collection upfront. No passwords, session cookies, or message contents are gathered.",
  },
  {
    icon: "dashboard",
    title: "Structured review console",
    text: "Plain language summaries for quick calls, plus an advanced mode for full forensic detail.",
  },
  {
    icon: "bolt",
    title: "Production grade stability",
    text: "Built for repeated screenshares and long review sessions, not throwaway demos.",
  },
];

export function LandingPage() {
  return (
    <div className="landing">
      <section className="hero">
        <div className="hero__content">
          <p className="hero__eyebrow">Roblox Screenshare &amp; Diagnostic Platform</p>
          <h1>
            Clear evidence.
            <br />
            <span className="hero__accent">Confident decisions.</span>
          </h1>
          <p className="hero__lead">
            Virello Secure helps reviewers verify Roblox executor risk with structured forensic scans,
            calibrated confidence scoring, and a workflow built for real screenshare cases.
          </p>
          <div className="hero__actions">
            <Link to="/download" className="btn btn--primary btn--lg">
              Download Scanner
            </Link>
            <Link to="/workspace" className="btn btn--outline btn--lg">
              Review Console
            </Link>
            <a className="btn btn--ghost btn--lg" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
              <IconDiscord size={18} />
              Discord
            </a>
          </div>
          <ul className="hero__trust">
            <li>Consent based collection</li>
            <li>40+ tracked executor brands</li>
            <li>6 minute scan budget</li>
          </ul>
        </div>
        <div className="hero__panel">
          <div className="hero__panel-inner">
            <div className="hero__stat">
              <span className="hero__stat-value">6 min</span>
              <span className="hero__stat-label">Primary scan delivery</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">40+</span>
              <span className="hero__stat-label">Executor brands tracked</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">15+</span>
              <span className="hero__stat-label">Forensic artifact sources</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">0</span>
              <span className="hero__stat-label">Session cookies collected</span>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <header className="section__header">
          <p className="section__eyebrow">Capabilities</p>
          <h2>Built for real screenshare workflows</h2>
          <p>Accuracy, clarity, and speed without sacrificing reviewer trust.</p>
        </header>
        <div className="feature-grid">
          {FEATURES.map((feature) => (
            <article key={feature.title} className="feature-card">
              <div className="feature-card__icon">
                <MaterialIcon name={feature.icon} size={24} />
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="cta-band">
        <div>
          <h2>Ready to review with confidence?</h2>
          <p>Download the scanner, sign in with Discord, and open the review console.</p>
        </div>
        <div className="cta-band__actions">
          <Link to="/download" className="btn btn--primary">
            Download Scanner
          </Link>
          <Link to="/workspace" className="btn btn--outline">
            Open Console
          </Link>
        </div>
      </section>
    </div>
  );
}
