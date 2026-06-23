import React from "react";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { IconDiscord } from "../components/VirelloIcons.jsx";
import { LegalDocument } from "../components/LegalPage.jsx";

const PLANS = [
  {
    id: "monthly",
    title: "Monthly License",
    blurb: "A simple month-to-month option for users who want full access without a long commitment.",
    price: "4.99€",
    period: "/ month",
    features: [
      "Full Executor scan access",
      "Unlimited scanner usage",
      "Ongoing scanner updates",
      "Discord full assistance",
    ],
  },
  {
    id: "quarterly",
    title: "3-Month License",
    blurb: "A balanced pick for steady users who want more time upfront and a better overall rate.",
    price: "12.99€",
    period: "/ 3 months",
    featured: true,
    features: [
      "Full Executor scan access",
      "Unlimited scanner usage",
      "Ongoing scanner updates",
      "Discord full assistance",
    ],
  },
  {
    id: "yearly",
    title: "Yearly License",
    blurb: "The strongest value for long-term protection, updates, and uninterrupted scanner access.",
    price: "39.99€",
    period: "/ year",
    features: [
      "Full Executor scan access",
      "Unlimited scanner usage",
      "Ongoing scanner updates",
      "Discord full assistance",
    ],
  },
];

export function PurchasePage() {
  return (
    <LegalDocument badge="Pricing" title="Choose your license" updated="June 2026">
      <p className="legal-doc__lead">
        All purchases are handled through our Discord server. Join, open a purchase lane, and staff will verify
        payment and activate your license.
      </p>

      <div className="pricing-grid">
        {PLANS.map((plan) => (
          <article key={plan.id} className={`pricing-card${plan.featured ? " pricing-card--featured" : ""}`}>
            {plan.featured ? <span className="pricing-card__badge">Popular</span> : null}
            <h2>{plan.title}</h2>
            <p className="pricing-card__blurb">{plan.blurb}</p>
            <p className="pricing-card__price">
              <strong>{plan.price}</strong>
              <span>{plan.period}</span>
            </p>
            <ul className="pricing-card__features">
              {plan.features.map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>

      <div className="pricing-cta">
        <h3>How to buy</h3>
        <p>
          Join the Virello Discord server and open a purchase ticket. Tell staff which plan you want, complete
          payment when asked, and your scanner access will be activated after verification.
        </p>
        <a className="btn btn--discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
          <IconDiscord size={18} />
          Join Discord to purchase
        </a>
      </div>
    </LegalDocument>
  );
}
