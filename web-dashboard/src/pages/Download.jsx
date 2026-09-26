import React from "react";
import { Link } from "react-router-dom";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { Reveal } from "../components/Reveal.jsx";
import { BRAND_FULL, DISCORD_INVITE_URL, SCANNER_DOWNLOAD_URL } from "../config/brand.js";
import { IconDiscord } from "../components/VirelloIcons.jsx";

const ICON_SOFT = "9b9ba3";

const REQUIREMENTS = [
  "Windows 10 or 11 (64-bit)",
  "Internet connection for PIN validation and report upload",
  "A valid PIN from a reviewer with console access",
  "Explicit consent before any data is collected",
];

const STEPS = [
  "Download and run the Virello scanner on the device being checked.",
  "Enter the PIN from your reviewer and read the consent summary.",
  "Start the scan and wait for it to finish.",
  "Your reviewer opens the completed report in the console.",
];

export function DownloadPage() {
  const hasDirectDownload = Boolean(SCANNER_DOWNLOAD_URL);

  return (
    <div className="download-page">
      <section className="download-hero">
        <Reveal className="download-hero__copy">
          <p className="download-hero__eyebrow">Desktop scanner</p>
          <h1>Download {BRAND_FULL}</h1>
          <p>
            Run a consent-first PC check on Windows. Your reviewer creates a PIN; you enter it here and approve
            what is collected before the scan starts.
          </p>
          <div className="download-hero__actions">
            {hasDirectDownload ? (
              <a href={SCANNER_DOWNLOAD_URL} className="btn btn--primary btn--lg" download>
                Download for Windows
              </a>
            ) : (
              <a href={DISCORD_INVITE_URL} className="btn btn--primary btn--lg" target="_blank" rel="noreferrer">
                <IconDiscord size={18} />
                Get download in Discord
              </a>
            )}
            <Link to="/workspace" className="btn btn--ghost btn--lg">
              Open console
            </Link>
          </div>
          {!hasDirectDownload ? (
            <p className="download-hero__note">
              The latest build is posted in Discord. Join and open the download lane for the current release.
            </p>
          ) : null}
        </Reveal>

        <Reveal className="download-hero__card" delay={60}>
          <div className="download-stat">
            <MaterialIcon name="timer" size={20} color={ICON_SOFT} />
            <div>
              <strong>Fast delivery</strong>
              <span>Results upload when the scan finishes</span>
            </div>
          </div>
          <div className="download-stat">
            <MaterialIcon name="consent" size={20} color={ICON_SOFT} />
            <div>
              <strong>Consent first</strong>
              <span>Nothing is collected until you approve</span>
            </div>
          </div>
          <div className="download-stat">
            <MaterialIcon name="windows" size={20} color={ICON_SOFT} />
            <div>
              <strong>Windows</strong>
              <span>64-bit desktop app</span>
            </div>
          </div>
        </Reveal>
      </section>

      <section className="download-grid">
        <Reveal className="download-panel" delay={40}>
          <h2>Requirements</h2>
          <ul>
            {REQUIREMENTS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Reveal>
        <Reveal className="download-panel" delay={80}>
          <h2>How it works</h2>
          <ol>
            {STEPS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        </Reveal>
      </section>
    </div>
  );
}
