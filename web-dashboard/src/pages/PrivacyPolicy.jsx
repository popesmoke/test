import React from "react";
import { LegalPage, LegalSection } from "../components/LegalPage.jsx";

export function PrivacyPolicyPage() {
  return (
    <LegalPage title="Privacy Policy" updated="June 2026">
      <p className="legal-intro">
        This Privacy Policy explains what information Virello collects through its website, Discord
        server, desktop scanner, and related services, and how that information is used.
      </p>

      <LegalSection title="Information we collect">
        <p>We may collect:</p>
        <ul>
          <li>Discord user ID, username, and avatar (for authentication and access verification)</li>
          <li>Diagnostic scan reports submitted with user consent via PIN sessions</li>
          <li>Device and application metadata required for forensic review (as disclosed at scan time)</li>
          <li>Messages and files submitted in Discord support or ticket lanes</li>
          <li>Payment proof provided for verification (screenshots or transaction references)</li>
          <li>Server roles, access permissions, and whitelist information</li>
          <li>Session PINs, scan status, and reviewer verdicts stored on our review platform</li>
        </ul>
      </LegalSection>

      <LegalSection title="Information we do not collect">
        <p>
          Virello does not intentionally collect, request, store, or process sensitive personal
          information, including:
        </p>
        <ul>
          <li>Passwords or authentication codes</li>
          <li>Two-factor authentication backups</li>
          <li>Banking credentials or credit card information</li>
          <li>Roblox session cookies (.ROBLOSECURITY) or browser session tokens</li>
          <li>Personal government identification documents</li>
          <li>Private message contents unrelated to support cases</li>
        </ul>
        <p>
          If such information is accidentally shared, users should notify staff immediately so
          appropriate action can be taken.
        </p>
      </LegalSection>

      <LegalSection title="How we use information">
        <p>Information may be used to:</p>
        <ul>
          <li>Operate PIN sessions and deliver scan results to authorized reviewers</li>
          <li>Verify purchases and grant product access</li>
          <li>Provide customer support through Discord lanes</li>
          <li>Enforce server rules, terms, and access policies</li>
          <li>Investigate disputes, abuse, or fraudulent activity</li>
          <li>Improve scan accuracy, platform stability, and service quality</li>
        </ul>
      </LegalSection>

      <LegalSection title="Storage">
        <p>
          Scan reports, session data, and service-related information are stored on systems used to
          operate the Virello platform and API. Payment verification materials remain within Discord
          channels according to server retention practices.
        </p>
      </LegalSection>

      <LegalSection title="Data sharing">
        <p>We do not sell user data.</p>
        <p>
          Information may be accessible to authorized Virello staff members who require access to
          perform support, moderation, payment verification, or service administration duties.
        </p>
        <p>Information may also be disclosed if required by law or legal process.</p>
      </LegalSection>

      <LegalSection title="Discord services">
        <p>
          Your use of Discord is also governed by{" "}
          <a href="https://discord.com/privacy" target="_blank" rel="noreferrer">
            Discord&apos;s Privacy Policy
          </a>{" "}
          and{" "}
          <a href="https://discord.com/terms" target="_blank" rel="noreferrer">
            Terms of Service
          </a>
          . Virello does not control Discord&apos;s collection, storage, or processing of data.
        </p>
      </LegalSection>

      <LegalSection title="Data retention">
        <p>
          Scan sessions may expire or be deleted after review. Moderation logs, backups, payment
          verification records, and other service-related records may be retained for operational,
          security, fraud-prevention, and dispute-resolution purposes.
        </p>
      </LegalSection>

      <LegalSection title="Your rights">
        <p>
          You may request information regarding data we hold about you by contacting server staff
          through a support lane.
        </p>
        <p>
          You may leave the Discord server at any time, though certain records may be retained where
          necessary for legitimate business, security, or legal purposes.
        </p>
      </LegalSection>

      <LegalSection title="Contact">
        <p>For privacy questions, open a Support lane in our Discord server or contact the server owner directly.</p>
      </LegalSection>
    </LegalPage>
  );
}
