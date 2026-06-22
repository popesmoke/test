import React from "react";
import { MessageCircle, Shield, Target, Users } from "lucide-react";
import { LegalPage, LegalSection } from "../components/LegalPage.jsx";
import { DISCORD_INVITE_URL } from "../config/brand.js";

export function AboutPage() {
  return (
    <LegalPage title="About Virello" updated="June 2026">
      <LegalSection title="Who we are">
        <p>
          Virello is a Roblox executor diagnostic platform built for reviewers who need fast checks,
          clear evidence, and reliable protection — without noisy setup or ambiguous results.
        </p>
        <p>
          We combine consent-first desktop scanning with a structured review console so support teams,
          community moderators, and screenshare reviewers can make confident decisions backed by
          forensic data.
        </p>
      </LegalSection>

      <LegalSection title="What we focus on">
        <ul>
          <li>Scanning and verifying Roblox executor-related risk signals across multiple artifact layers.</li>
          <li>License-based access protection tied to verified Discord roles.</li>
          <li>Continuous detection updates delivered through our Discord community.</li>
          <li>Low false-positive scoring with evidence reliability tiers and cross-source correlation.</li>
        </ul>
      </LegalSection>

      <LegalSection title="How we work">
        <p>
          Purchases, support, verification, and account help run through private Discord lanes so
          every user can keep their case organized with staff. The review console on this site is
          where verified reviewers manage PIN sessions and inspect completed scans.
        </p>
        <div className="about-cards">
          <div className="about-card">
            <Shield size={20} />
            <strong>Secure by design</strong>
            <p>No passwords, .ROBLOSECURITY cookies, or message contents are collected during scans.</p>
          </div>
          <div className="about-card">
            <Target size={20} />
            <strong>Accuracy first</strong>
            <p>Detection is calibrated for real-world screenshare — strong evidence only when corroborated.</p>
          </div>
          <div className="about-card">
            <Users size={20} />
            <strong>Community-driven</strong>
            <p>Updates, support, and access verification flow through our Discord server.</p>
          </div>
        </div>
      </LegalSection>

      <LegalSection title="Get in touch">
        <p>
          For support, access questions, or partnership inquiries, join our Discord community and open
          a support lane.
        </p>
        <a className="about-discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
          <MessageCircle size={18} />
          Join Virello Discord
        </a>
      </LegalSection>
    </LegalPage>
  );
}
