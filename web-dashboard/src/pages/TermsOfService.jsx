import React from "react";
import { LegalPage, LegalSection } from "../components/LegalPage.jsx";

export function TermsOfServicePage() {
  return (
    <LegalPage title="Terms of Service" updated="June 2026">
      <p className="legal-intro">
        These Terms of Service govern your use of the Virello website, Discord server, desktop
        scanner, review console, and related services. By accessing or using our services, you agree
        to these Terms.
      </p>

      <LegalSection title="Service">
        <p>
          Virello provides digital diagnostic tools, subscriptions, and support through Discord and
          this review platform. Features, pricing, availability, and service offerings may be
          modified, suspended, or discontinued at any time without prior notice.
        </p>
        <p>
          Scan results are forensic indicators intended to assist human reviewers. They do not
          constitute definitive proof of cheating and should be interpreted in context.
        </p>
      </LegalSection>

      <LegalSection title="Eligibility">
        <p>
          You must comply with Discord&apos;s Terms of Service and Community Guidelines and be legally
          capable of entering into this agreement in your jurisdiction.
        </p>
      </LegalSection>

      <LegalSection title="Accounts and access">
        <p>
          Access to products and services is tied to your Discord account and any roles assigned
          after a verified purchase or staff approval.
        </p>
        <p>
          Sharing, transferring, reselling, or granting access to others is prohibited unless
          explicitly authorized by Virello staff.
        </p>
      </LegalSection>

      <LegalSection title="Scanner use and consent">
        <p>
          The desktop scanner collects diagnostic data only after explicit user consent. Users must
          be informed of what is collected before a scan begins. Reviewers must use scan data only
          for legitimate moderation, support, or screenshare purposes.
        </p>
      </LegalSection>

      <LegalSection title="Payments">
        <p>
          All payments must be completed using the methods provided in the Purchase Panel or
          Purchase Lane. Payments are manually reviewed and verified by staff before access is
          granted.
        </p>
      </LegalSection>

      <LegalSection title="Subscriptions and cancellation">
        <p>
          Certain services may be provided on a monthly subscription basis. You may cancel your
          subscription at any time to prevent future billing. Cancellation does not entitle you to a
          refund for the current billing period.
        </p>
      </LegalSection>

      <LegalSection title="Refund policy">
        <p>All sales are final.</p>
        <p>
          Due to the nature of digital goods and services, refunds, partial refunds, and prorated
          refunds are not provided once access has been delivered, except where required by
          applicable law or in cases of verified billing errors at staff discretion.
        </p>
      </LegalSection>

      <LegalSection title="Chargebacks and disputes">
        <p>Users must contact staff before initiating a payment dispute or chargeback.</p>
        <p>Unauthorized chargebacks or payment reversals may result in:</p>
        <ul>
          <li>Immediate termination of access</li>
          <li>Permanent removal from Virello services</li>
          <li>Restriction from future purchases</li>
        </ul>
      </LegalSection>

      <LegalSection title="Limitation of liability">
        <p>
          Virello services are provided &quot;as is&quot; and &quot;as available&quot; without warranties of any kind.
        </p>
        <p>
          To the fullest extent permitted by law, Virello shall not be liable for any indirect,
          incidental, consequential, special, or punitive damages arising from the use of our
          services, including decisions made based on scan results.
        </p>
      </LegalSection>

      <LegalSection title="Termination">
        <p>
          We reserve the right to suspend or terminate access to our services at any time for
          violations of these Terms, abuse of our systems, fraudulent activity, or any behavior
          deemed harmful to the community or service.
        </p>
      </LegalSection>

      <LegalSection title="Changes to these terms">
        <p>We may update these Terms at any time.</p>
        <p>
          Continued use of Virello services after changes are posted constitutes acceptance of the
          revised Terms.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
