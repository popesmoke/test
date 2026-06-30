import React from "react";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { IconDiscord } from "../components/VirelloIcons.jsx";
import { LegalArticle, LegalDocument } from "../components/LegalPage.jsx";

export function AboutPage() {
  return (
    <LegalDocument badge="About" title="Who we are" updated="June 2026">
      <p className="legal-doc__lead">
        Virello helps reviewers run fast Roblox screenshare checks with clear results and steady
        protection, without a messy setup or vague verdicts.
      </p>

      <LegalArticle index="I" title="What we focus on">
        <ul>
          <li>Scanning and checking Roblox executor risk on Windows PCs</li>
          <li>License based access tied to verified Discord roles</li>
          <li>Regular detection updates through our community</li>
          <li>Low false positive scoring with clear evidence tiers</li>
        </ul>
      </LegalArticle>

      <LegalArticle index="II" title="How we work">
        <p>
          Purchases, support, verification, and account help run through private Discord lanes. The
          review console on this site is where verified reviewers manage PIN sessions and read scans.
        </p>
        <div className="about-cards">
          <div className="about-card">
            <MaterialIcon name="lock" size={22} />
            <strong>Secure by design</strong>
            <p>No passwords, .ROBLOSECURITY cookies, or message contents are collected.</p>
          </div>
          <div className="about-card">
            <MaterialIcon name="track_changes" size={22} />
            <strong>Accuracy first</strong>
            <p>Strong calls only when multiple signals line up on the same scan.</p>
          </div>
          <div className="about-card">
            <MaterialIcon name="groups" size={22} />
            <strong>Community driven</strong>
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
