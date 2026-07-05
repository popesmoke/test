import React from "react";
import { Link } from "react-router-dom";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { Reveal } from "../components/Reveal.jsx";
import { BRAND_FULL, DISCORD_INVITE_URL, SCANNER_DOWNLOAD_URL } from "../config/brand.js";
import { IconDiscord } from "../components/VirelloIcons.jsx";

const ICON_ACCENT = "ff4d5f";
const ICON_SOFT = "ff8d9a";

const REQUIREMENTS = [
  "Windows 10 or 11 (64-bit)",
  "Active internet connection for PIN validation and report upload",
  "A valid PIN from a reviewer with console access",
  "Explicit consent before any data is collected",
];

const STEPS = [
  "Download and run the Virello scanner on the device being checked.",
  "Enter the PIN provided by your reviewer and read the consent summary.",
  "Start the scan and wait for it to finish.",
  "Your reviewer views the completed report in the Review Console.",
];

export function DownloadPage() {
  const hasDirectDownload = Boolean(SCANNER_DOWNLOAD_URL);

  return (
    <div className="download-page">
      <section className="download-hero">
        <Reveal className="download-hero__copy">
          <p className="download-hero__eyebrow">Desktop Scanner</p>
          <h1>Download {BRAND_FULL}</h1>
          <p>
            The Virello desktop app runs a PC check with explicit user consent.
            Reviewers generate a PIN in the console. Users run this app to complete the scan.
          </p>
          <div className="download-hero__actions">
            {hasDirectDownload ? (
              <a href={SCANNER_DOWNLOAD_URL} className="btn btn--primary btn--lg" download>
                <MaterialIcon name="download" size={20} color="ffffff" />
                Download for Windows
              </a>
            ) : (
              <a href={DISCORD_INVITE_URL} className="btn btn--primary btn--lg" target="_blank" rel="noreferrer">
                <IconDiscord size={20} />
                Get download from Discord
              </a>
            )}
            <Link to="/workspace" className="btn btn--ghost btn--lg">
              Open review console
            </Link>
          </div>
          {!hasDirectDownload ? (
            <p className="download-hero__note">
              The latest build is distributed through our Discord server. Join and open the download lane for the current release.
            </p>
          ) : null}
        </Reveal>

        <Reveal className="download-hero__card" delay={100}>
          <div className="download-stat">
            <MaterialIcon name="timer" size={24} color={ICON_SOFT} />
            <div>
              <strong>Fast delivery</strong>
              <span>Results upload when the scan finishes</span>
            </div>
          </div>
          <div className="download-stat">
            <MaterialIcon name="consent" size={24} color={ICON_SOFT} />
            <div>
              <strong>Consent first</strong>
              <span>No hidden collection</span>
            </div>
          </div>
          <div className="download-stat">
            <MaterialIcon name="windows" size={24} color={ICON_SOFT} />
            <div>
              <strong>Windows</strong>
              <span>64-bit desktop app</span>
            </div>
          </div>
        </Reveal>
      </section>

      <section className="download-grid">
        <Reveal className="download-panel" delay={60}>
          <h2>Requirements</h2>
          <ul>
            {REQUIREMENTS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Reveal>
        <Reveal className="download-panel" delay={120}>
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
