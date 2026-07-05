import React from "react";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { Reveal } from "../components/Reveal.jsx";
import { IconDiscord } from "../components/VirelloIcons.jsx";
import { LegalArticle, LegalDocument } from "../components/LegalPage.jsx";

const ICON_ACCENT = "ff4d5f";

export function AboutPage() {
  return (
    <LegalDocument badge="About" title="Who we are" updated="June 2026">
      <p className="legal-doc__lead">
        Virello helps reviewers run fast Roblox screenshare checks with clear results, without a messy
        setup or vague verdicts.
      </p>

      <Reveal>
        <LegalArticle index="I" title="What we focus on">
          <ul>
            <li>PC checks for Roblox screenshare and support workflows</li>
            <li>License-based access tied to verified Discord roles</li>
            <li>Regular product updates through our community</li>
            <li>Clear result summaries reviewers can explain live</li>
          </ul>
        </LegalArticle>
      </Reveal>

      <Reveal delay={80}>
        <LegalArticle index="II" title="How we work">
          <p>
            Purchases, support, verification, and account help run through private Discord lanes. The
            review console on this site is where verified reviewers manage PIN sessions and read scans.
          </p>
          <div className="about-cards">
            <div className="about-card">
              <MaterialIcon name="lock" size={24} color={ICON_ACCENT} />
              <strong>Secure by design</strong>
              <p>Sensitive credentials and private messages are never collected.</p>
            </div>
            <div className="about-card">
              <MaterialIcon name="verified" size={24} color={ICON_ACCENT} />
              <strong>Clear verdicts</strong>
              <p>Results are structured so your team can review them together on a call.</p>
            </div>
            <div className="about-card">
              <MaterialIcon name="groups" size={24} color={ICON_ACCENT} />
              <strong>Community driven</strong>
              <p>Updates, support, and access verification flow through Discord.</p>
            </div>
          </div>
        </LegalArticle>
      </Reveal>

      <Reveal delay={160}>
        <LegalArticle index="III" title="Contact">
          <p>For support or access questions, join our Discord and open a support lane.</p>
          <a className="btn btn--discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
            <IconDiscord size={18} />
            Join Virello Discord
          </a>
        </LegalArticle>
      </Reveal>
    </LegalDocument>
  );
}
