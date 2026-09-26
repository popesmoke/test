import React from "react";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { Reveal } from "../components/Reveal.jsx";
import { IconDiscord } from "../components/VirelloIcons.jsx";
import { LegalDocument } from "../components/LegalPage.jsx";

const PLANS = [
  {
    id: "monthly",
    title: "Monthly",
    blurb: "Full access, billed monthly. Cancel anytime through Discord support.",
    price: "4.99€",
    period: "/ month",
    features: ["Full scan access", "Unlimited scanner use", "Product updates", "Discord support"],
  },
  {
    id: "quarterly",
    title: "3 months",
    blurb: "Better rate for teams that run checks regularly.",
    price: "12.99€",
    period: "/ 3 months",
    featured: true,
    features: ["Full scan access", "Unlimited scanner use", "Product updates", "Discord support"],
  },
  {
    id: "yearly",
    title: "Yearly",
    blurb: "Best value for uninterrupted access across the year.",
    price: "39.99€",
    period: "/ year",
    features: ["Full scan access", "Unlimited scanner use", "Product updates", "Discord support"],
  },
];

export function PurchasePage() {
  return (
    <LegalDocument badge="Pricing" title="Licenses" updated="June 2026">
      <p className="legal-doc__lead">
        Buy through Discord. Staff verify payment and activate your Access role for the review console.
      </p>

      <div className="pricing-grid">
        {PLANS.map((plan, i) => (
          <Reveal
            key={plan.id}
            className={`pricing-card${plan.featured ? " pricing-card--featured" : ""}`}
            delay={i * 50}
          >
            <div className="pricing-card__head">
              {plan.featured ? (
                <span className="pricing-card__badge">Popular</span>
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

      <Reveal className="pricing-cta" delay={120}>
        <h3>How to buy</h3>
        <p>
          Join Discord, open a purchase ticket, pick a plan, and complete payment when staff ask (PayPal, crypto,
          or methods shown there). Access is activated after verification.
        </p>
        <a className="btn btn--discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
          <IconDiscord size={18} />
          Join Discord to purchase
        </a>
      </Reveal>
    </LegalDocument>
  );
}
