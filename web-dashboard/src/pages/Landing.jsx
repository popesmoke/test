import React from "react";
import { Link } from "react-router-dom";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { IconDiscord } from "../components/VirelloIcons.jsx";

export function LandingPage() {
  return (
    <div className="landing">
      <section className="hero hero--asymmetric">
        <div className="hero__content">
          <p className="hero__eyebrow">Windows screenshare reviews</p>
          <h1>PC scans for live reviews</h1>
          <p className="hero__lead">
            User approves the scan. You get a ranked report in the review console.
          </p>
          <div className="hero__actions">
            <Link to="/download" className="btn btn--primary btn--lg">
              Download scanner
            </Link>
            <Link to="/workspace" className="btn btn--outline btn--lg">
              Open console
            </Link>
            <a className="btn btn--ghost btn--lg" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
              <IconDiscord size={18} />
              Discord
            </a>
          </div>
          <ul className="hero__trust">
            <li>Consent before upload</li>
            <li>Watch lists you control</li>
            <li>Most scans take about 5 minutes</li>
          </ul>
        </div>
        <aside className="hero__panel">
          <div className="hero__panel-inner">
            <div className="hero__stat hero__stat--highlight">
              <MaterialIcon name="timer" size={22} />
              <span className="hero__stat-value">5 min</span>
              <span className="hero__stat-label">Typical scan time</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">PIN</span>
              <span className="hero__stat-label">Links the scan to your console session</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">Win 10+</span>
              <span className="hero__stat-label">Windows desktop scanner</span>
            </div>
          </div>
          <p className="hero__panel-note muted">
            Reviewers sign in with Discord. Scanned users do not need an account.
          </p>
        </aside>
      </section>

      <section className="cta-band">
        <div>
          <h2>Get started</h2>
          <p>Download the scanner, make a PIN in the console, and share it during screenshare.</p>
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

      <p className="landing-attribution">
        Icons by <a href="https://icons8.com" target="_blank" rel="noreferrer">Icons8</a>
      </p>
    </div>
  );
}
