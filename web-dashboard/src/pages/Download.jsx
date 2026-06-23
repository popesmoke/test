import React from "react";
import { Link } from "react-router-dom";
import { BRAND_FULL, DISCORD_INVITE_URL, SCANNER_DOWNLOAD_URL } from "../config/brand.js";
import { IconConsent, IconDiscord, IconDownload, IconTimer, IconWindows } from "../components/VirelloIcons.jsx";

const REQUIREMENTS = [
  "Windows 10 or 11 (64-bit)",
  "Active internet connection for PIN validation and report upload",
  "A valid PIN from a reviewer with console access",
  "Explicit consent before any data is collected",
];

const STEPS = [
  "Download and run the Virello scanner on the device being checked.",
  "Enter the PIN provided by your reviewer and read the consent summary.",
  "Start the scan. Primary results are delivered within six minutes.",
  "Your reviewer views the completed report in the Review Console.",
];

export function DownloadPage() {
  const hasDirectDownload = Boolean(SCANNER_DOWNLOAD_URL);

  return (
    <div className="download-page">
      <section className="download-hero">
        <div className="download-hero__copy">
          <p className="download-hero__eyebrow">Desktop Scanner</p>
          <h1>Download {BRAND_FULL}</h1>
          <p>
            The Virello desktop scanner runs a full PC check with explicit user consent.
            Reviewers generate a PIN in the console. Users run this app to complete the scan.
          </p>
          <div className="download-hero__actions">
            {hasDirectDownload ? (
              <a href={SCANNER_DOWNLOAD_URL} className="btn btn--primary btn--lg" download>
                <IconDownload size={20} />
                Download for Windows
              </a>
            ) : (
              <a href={DISCORD_INVITE_URL} className="btn btn--primary btn--lg" target="_blank" rel="noreferrer">
                <IconDiscord size={20} />
                Get Download from Discord
              </a>
            )}
            <Link to="/workspace" className="btn btn--ghost btn--lg">
              Open Review Console
            </Link>
          </div>
          {!hasDirectDownload ? (
            <p className="download-hero__note">
              The latest build is distributed through our Discord server. Join and open the download lane for the current release.
            </p>
          ) : null}
        </div>
        <aside className="download-hero__card">
          <div className="download-stat">
            <IconTimer size={22} />
            <div>
              <strong>6 min</strong>
              <span>Primary scan delivery</span>
            </div>
          </div>
          <div className="download-stat">
            <IconConsent size={22} />
            <div>
              <strong>Consent first</strong>
              <span>No hidden collection</span>
            </div>
          </div>
          <div className="download-stat">
            <IconWindows size={22} />
            <div>
              <strong>Windows</strong>
              <span>64-bit desktop app</span>
            </div>
          </div>
        </aside>
      </section>

      <section className="download-grid">
        <article className="download-panel">
          <h2>Requirements</h2>
          <ul>
            {REQUIREMENTS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="download-panel">
          <h2>How scanning works</h2>
          <ol>
            {STEPS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        </article>
      </section>
    </div>
  );
}
