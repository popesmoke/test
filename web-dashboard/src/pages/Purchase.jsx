import React from "react";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { Reveal } from "../components/Reveal.jsx";
import { IconDiscord } from "../components/VirelloIcons.jsx";
import { LegalDocument } from "../components/LegalPage.jsx";

const PLANS = [
  {
    id: "monthly",
    title: "Monthly",
    blurb: "Full access on a monthly plan. Cancel anytime.",
    price: "4.99€",
    period: "/ month",
    features: [
      "Full executor scan access",
      "Unlimited scanner usage",
      "Ongoing scanner updates",
      "Discord support",
    ],
  },
  {
    id: "quarterly",
    title: "3 months",
    blurb: "Better rate for teams that review regularly.",
    price: "12.99€",
    period: "/ 3 months",
    featured: true,
    features: [
      "Full executor scan access",
      "Unlimited scanner usage",
      "Ongoing scanner updates",
      "Discord support",
    ],
  },
  {
    id: "yearly",
    title: "Yearly",
    blurb: "Best value for long-term access and updates.",
    price: "39.99€",
    period: "/ year",
    features: [
      "Full executor scan access",
      "Unlimited scanner usage",
      "Ongoing scanner updates",
      "Discord support",
    ],
  },
];

export function PurchasePage() {
  return (
    <LegalDocument badge="Pricing" title="Choose your license" updated="June 2026">
      <p className="legal-doc__lead">
        All purchases go through our Discord server. Join, open a purchase lane, and staff will verify
        payment and activate your license.
      </p>

      <div className="pricing-grid">
        {PLANS.map((plan, i) => (
          <Reveal
            key={plan.id}
            className={`pricing-card${plan.featured ? " pricing-card--featured" : ""}`}
            delay={i * 80}
          >
            <div className="pricing-card__head">
              {plan.featured ? (
                <span className="pricing-card__badge">Most popular</span>
              ) : (
                <span className="pricing-card__badge pricing-card__badge--placeholder" aria-hidden="true" />
              )}
              <h2>{plan.title}</h2>
              <p className="pricing-card__blurb">{plan.blurb}</p>
            </div>
            <div className="pricing-card__body">
              <p className="pricing-card__price">
                <strong>{plan.price}</strong>
                <span>{plan.period}</span>
              </p>
              <ul className="pricing-card__features">
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
            </div>
          </Reveal>
        ))}
      </div>

      <Reveal className="pricing-cta" delay={200}>
        <h3>How to buy</h3>
        <p>
          Join the Virello Discord server and open a purchase ticket. Tell staff which plan you want, complete
          payment when asked, and your scanner access will be activated after verification.
        </p>
        <a className="btn btn--discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
          <IconDiscord size={18} />
          Join Discord to purchase
        </a>
      </Reveal>
    </LegalDocument>
  );
}
