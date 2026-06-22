import React from "react";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { IconDiscord, IconLock, IconTarget, IconUsers } from "../components/VirelloIcons.jsx";
import { LegalArticle, LegalDocument } from "../components/LegalPage.jsx";

export function AboutPage() {
  return (
    <LegalDocument badge="About" title="Who" highlight="We Are" updated="June 2026">
      <p className="legal-doc__lead">
        Virello is a Roblox executor diagnostic platform for reviewers who need fast checks, clear
        evidence, and steady protection — without noisy setup or ambiguous results.
      </p>

      <LegalArticle index="I" title="What we focus on">
        <ul>
          <li>Scanning and verifying Roblox executor risk across multiple forensic layers</li>
          <li>License-based access tied to verified Discord roles</li>
          <li>Continuous detection updates through our community</li>
          <li>Low false-positive scoring with evidence reliability tiers</li>
        </ul>
      </LegalArticle>

      <LegalArticle index="II" title="How we work">
        <p>
          Purchases, support, verification, and account help run through private Discord lanes. The
          review console on this site is where verified reviewers manage PIN sessions and inspect scans.
        </p>
        <div className="about-cards">
          <div className="about-card">
            <IconLock size={22} />
            <strong>Secure by design</strong>
            <p>No passwords, .ROBLOSECURITY cookies, or message contents are collected.</p>
          </div>
          <div className="about-card">
            <IconTarget size={22} />
            <strong>Accuracy first</strong>
            <p>Strong evidence only when corroborated across multiple artifact sources.</p>
          </div>
          <div className="about-card">
            <IconUsers size={22} />
            <strong>Community-driven</strong>
            <p>Updates, support, and access verification flow through Discord.</p>
          </div>
        </div>
      </LegalArticle>

      <LegalArticle index="III" title="Contact">
        <p>For support or access questions, join our Discord and open a support lane.</p>
        <a className="btn btn--discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
          <IconDiscord size={18} />
          Join Virello Discord
        </a>
      </LegalArticle>
    </LegalDocument>
  );
}
