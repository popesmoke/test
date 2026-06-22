import React from "react";
import { LegalArticle, LegalDocument } from "../components/LegalPage.jsx";

export function PrivacyPolicyPage() {
  return (
    <LegalDocument
      badge="Privacy"
      title="Virello"
      highlight="Privacy Policy"
      updated="June 22, 2026"
      meta={["Applies to website, Discord, and desktop scanner"]}
    >
      <p className="legal-doc__lead">
        This policy describes what Virello collects through its website, Discord community, desktop
        scanner, and review platform — and what we deliberately avoid collecting.
      </p>

      <LegalArticle index="I" title="Information we collect">
        <ul>
          <li>Discord user ID, username, and avatar for authentication and access verification</li>
          <li>Diagnostic scan reports submitted with explicit user consent via PIN sessions</li>
          <li>Device and application metadata disclosed at scan time for forensic review</li>
          <li>Messages and files submitted in Discord support or ticket lanes</li>
          <li>Payment proof for verification (screenshots or transaction references)</li>
          <li>Server roles, access permissions, and whitelist status</li>
          <li>Session PINs, scan status, and reviewer verdicts on the review platform</li>
        </ul>
      </LegalArticle>

      <LegalArticle index="II" title="Information we do not collect">
        <p>Virello does not intentionally collect or process:</p>
        <ul>
          <li>Passwords, authentication codes, or two-factor backups</li>
          <li>Banking credentials or credit card numbers</li>
          <li>Roblox session cookies (.ROBLOSECURITY) or browser session tokens</li>
          <li>Government identification documents</li>
          <li>Private message contents unrelated to support cases</li>
        </ul>
        <p className="legal-doc__callout">
          If sensitive data is accidentally shared, notify staff immediately so it can be removed.
        </p>
      </LegalArticle>

      <LegalArticle index="III" title="How information is used">
        <ul>
          <li>Operate PIN sessions and deliver scan results to authorized reviewers</li>
          <li>Verify purchases and grant product access</li>
          <li>Provide customer support through Discord lanes</li>
          <li>Enforce server rules, terms, and access policies</li>
          <li>Investigate disputes, abuse, or fraudulent activity</li>
          <li>Improve scan accuracy, stability, and service quality</li>
        </ul>
      </LegalArticle>

      <LegalArticle index="IV" title="Storage and retention">
        <p>
          Scan reports and session data are stored on systems operating the Virello platform. Payment
          verification materials remain in Discord channels per server retention practices.
        </p>
        <p>
          Sessions may expire or be deleted after review. Moderation logs, backups, and verification
          records may be retained for security, fraud prevention, and dispute resolution.
        </p>
      </LegalArticle>

      <LegalArticle index="V" title="Sharing and third parties">
        <p><strong>We do not sell user data.</strong></p>
        <p>
          Authorized Virello staff may access information for support, moderation, verification, or
          administration. Data may be disclosed when required by law.
        </p>
        <p>
          Discord&apos;s own policies govern your use of Discord — see{" "}
          <a href="https://discord.com/privacy" target="_blank" rel="noreferrer">discord.com/privacy</a>.
        </p>
      </LegalArticle>

      <LegalArticle index="VI" title="Your rights and contact">
        <p>
          Request information about data we hold by contacting staff through a support lane in Discord.
          You may leave the server at any time; certain records may be retained where legally necessary.
        </p>
      </LegalArticle>
    </LegalDocument>
  );
}
