import React from "react";
import { LegalArticle, LegalDocument } from "../components/LegalPage.jsx";

export function TermsOfServicePage() {
  return (
    <LegalDocument
      badge="Terms"
      title="Virello Terms of Service"
      updated="June 22, 2026"
      meta={["By using Virello you agree to these terms"]}
    >
      <p className="legal-doc__lead">
        These terms govern your use of the Virello website, Discord server, desktop scanner, review
        console, and related services.
      </p>

      <LegalArticle index="I" title="Service description">
        <p>
          Virello provides digital diagnostic tools, subscriptions, and support through Discord and
          this review platform. Features, pricing, and availability may change without prior notice.
        </p>
        <p className="legal-doc__callout">
          Scan results are forensic indicators to assist human reviewers, not definitive proof of
          cheating. Interpret results in context.
        </p>
      </LegalArticle>

      <LegalArticle index="II" title="Eligibility and accounts">
        <p>
          You must comply with Discord&apos;s Terms of Service and Community Guidelines and be legally
          capable of entering this agreement in your jurisdiction.
        </p>
        <p>
          Access is tied to your Discord account and assigned roles after verified purchase or staff
          approval. Sharing, reselling, or transferring access is prohibited unless explicitly authorized.
        </p>
      </LegalArticle>

      <LegalArticle index="III" title="Scanner use and consent">
        <p>
          The desktop scanner collects diagnostic data only after explicit user consent. Users must be
          informed before a scan begins. Reviewers must use scan data only for legitimate moderation,
          support, or screenshare purposes.
        </p>
      </LegalArticle>

      <LegalArticle index="IV" title="Payments and subscriptions">
        <p>
          Payments must use methods provided in the Purchase Panel or Purchase Lane and are manually
          verified before access is granted.
        </p>
        <p>
          Subscriptions may renew monthly. Cancel anytime to stop future billing. Cancellation does not
          refund the current period.
        </p>
      </LegalArticle>

      <LegalArticle index="V" title="Refund policy">
        <p><strong>All sales are final.</strong></p>
        <p>
          Due to the nature of digital goods, refunds are not provided once access is delivered, except
          where required by law or for verified billing errors at staff discretion.
        </p>
      </LegalArticle>

      <LegalArticle index="VI" title="Chargebacks and disputes">
        <p>Contact staff before initiating a payment dispute or chargeback.</p>
        <p>Unauthorized chargebacks may result in:</p>
        <ul>
          <li>Immediate termination of access</li>
          <li>Permanent removal from Virello services</li>
          <li>Restriction from future purchases</li>
        </ul>
      </LegalArticle>

      <LegalArticle index="VII" title="Liability and termination">
        <p>
          Services are provided &quot;as is&quot; without warranties. To the fullest extent permitted by law,
          Virello is not liable for indirect, incidental, or consequential damages, including decisions
          based on scan results.
        </p>
        <p>
          We may suspend or terminate access for violations, abuse, fraud, or behavior harmful to the
          community. Terms may be updated at any time; continued use constitutes acceptance.
        </p>
      </LegalArticle>
    </LegalDocument>
  );
}
