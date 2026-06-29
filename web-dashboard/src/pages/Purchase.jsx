import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { IconDiscord } from "../components/VirelloIcons.jsx";
import { LegalDocument } from "../components/LegalPage.jsx";
import { createCheckoutSession, fetchPricing } from "../lib/siteApi.js";
import { getStoredToken, startDiscordLogin } from "../lib/auth.js";

function PlanCard({ plan, onBuy, checkoutBusy, stripeEnabled }) {
  return (
    <article className={`pricing-card${plan.featured ? " pricing-card--featured" : ""}`}>
      <div className="pricing-card__head">
        {plan.featured ? (
          <span className="pricing-card__badge">Best value</span>
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
        {stripeEnabled ? (
          <button
            type="button"
            className="btn btn--primary pricing-card__buy"
            disabled={checkoutBusy}
            onClick={() => onBuy(plan.id)}
          >
            Pay with card
          </button>
        ) : null}
      </div>
    </article>
  );
}

export function PurchasePage() {
  const [pricing, setPricing] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    void fetchPricing()
      .then(setPricing)
      .catch((caught) => setError(caught.message));
  }, []);

  useEffect(() => {
    const checkout = searchParams.get("checkout");
    if (checkout === "success") {
      setNotice("Payment received. Your access will activate shortly after verification.");
    } else if (checkout === "cancel") {
      setNotice("Checkout was cancelled. You can try again or pay via Discord.");
    }
  }, [searchParams]);

  const altPayments = pricing?.alt_payments || [];
  const stripeEnabled = Boolean(pricing?.stripe_enabled);

  const altPaymentLabel = useMemo(
    () => altPayments.map((item) => item.label).join(", "),
    [altPayments],
  );

  async function handleBuy(planId) {
    const token = getStoredToken();
    if (!token) {
      await startDiscordLogin("/purchase");
      return;
    }
    setCheckoutBusy(true);
    setError("");
    try {
      const session = await createCheckoutSession(token, planId);
      if (session.url) {
        window.location.assign(session.url);
        return;
      }
      throw new Error("Stripe did not return a checkout URL.");
    } catch (caught) {
      if (caught.code === "stripe_unavailable" || caught.code === "stripe_price_missing") {
        setError(`${caught.message} Join Discord for ${altPaymentLabel || "alternative payments"}.`);
      } else {
        setError(caught.message);
      }
    } finally {
      setCheckoutBusy(false);
    }
  }

  return (
    <LegalDocument badge="Pricing" title="Choose your license" updated="June 2026">
      <p className="legal-doc__lead">
        Personal plans for solo reviewers. Enterprise tiers add team seats, branding, and priority support — priced below comparable tools.
      </p>

      {notice ? <div className="notice-banner">{notice}</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}

      {!pricing ? <p className="muted">Loading plans…</p> : null}

      {pricing ? (
        <>
          <h3 className="pricing-section-title">Personal</h3>
          <div className="pricing-grid">
            {pricing.personal.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                onBuy={handleBuy}
                checkoutBusy={checkoutBusy}
                stripeEnabled={stripeEnabled}
              />
            ))}
          </div>

          <h3 className="pricing-section-title">Enterprise</h3>
          <p className="pricing-section-lead muted">
            Multi-seat licenses for staff teams. Includes enterprise management, custom report branding, and priority support.
          </p>
          <div className="pricing-grid pricing-grid--enterprise">
            {pricing.enterprise.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                onBuy={handleBuy}
                checkoutBusy={checkoutBusy}
                stripeEnabled={stripeEnabled}
              />
            ))}
          </div>
        </>
      ) : null}

      <div className="pricing-cta">
        <h3>Other payment methods</h3>
        <p>
          {stripeEnabled
            ? "Card checkout is available above. For PayPal, Greek Paysafe, Litecoin, or Ethereum, open a purchase ticket in Discord — staff will verify payment and activate your license."
            : `Card checkout is not live yet. Join Discord to pay with ${altPaymentLabel || "PayPal, Greek Paysafe, Litecoin, or Ethereum"}.`}
        </p>
        <a className="btn btn--discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
          <IconDiscord size={18} />
          Join Discord to purchase
        </a>
      </div>

      <p className="muted pricing-footnote">
        Stripe checkout: card{stripeEnabled ? "" : " (coming soon)"}. Alternative methods are handled manually in Discord.
      </p>
    </LegalDocument>
  );
}
