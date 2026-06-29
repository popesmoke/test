import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { DISCORD_INVITE_URL, SHOPPEX_STORE_URL } from "../config/brand.js";
import { IconDiscord } from "../components/VirelloIcons.jsx";
import { LegalDocument } from "../components/LegalPage.jsx";
import { createCheckoutSession, fetchPricing } from "../lib/siteApi.js";
import { getStoredToken, startDiscordLogin } from "../lib/auth.js";

function PaymentMethodList({ title, methods }) {
  if (!methods?.length) {
    return null;
  }
  return (
    <div className="pricing-payment-group">
      <h4>{title}</h4>
      <ul className="pricing-payment-list">
        {methods.map((method) => (
          <li key={method.id}>{method.label}</li>
        ))}
      </ul>
    </div>
  );
}

function resolvePlanStoreUrl(plan, shoppexPlanUrls, storeUrl) {
  const fromApi = shoppexPlanUrls.get(plan.id);
  if (fromApi) {
    return fromApi;
  }
  const slug = String(plan.shoppex_slug || "").trim();
  if (storeUrl && slug) {
    return `${storeUrl}/product/${slug}`;
  }
  return storeUrl;
}

function PlanCard({ plan, onBuy, checkoutBusy, stripeEnabled, shoppexUrl }) {
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
        <div className="pricing-card__actions">
          {shoppexUrl ? (
            <a className="btn btn--primary pricing-card__buy" href={shoppexUrl} target="_blank" rel="noreferrer">
              Buy on store
            </a>
          ) : (
            <a className="btn btn--primary pricing-card__buy" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
              <IconDiscord size={18} />
              Buy via Discord
            </a>
          )}
          {stripeEnabled ? (
            <button
              type="button"
              className="btn btn--ghost pricing-card__buy"
              disabled={checkoutBusy}
              onClick={() => onBuy(plan.id)}
            >
              Pay with card
            </button>
          ) : null}
        </div>
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
      setNotice("Checkout was cancelled. You can try again or pay through the store or Discord.");
    }
  }, [searchParams]);

  const shoppexPayments = pricing?.shoppex_payments || [];
  const discordTicketPayments = pricing?.discord_ticket_payments || [];
  const stripeEnabled = Boolean(pricing?.stripe_enabled);

  const shoppexStoreUrl = useMemo(() => {
    const fromApi = String(pricing?.shoppex_store_url || "").trim().replace(/\/$/, "");
    const fromBrand = String(SHOPPEX_STORE_URL || "").trim().replace(/\/$/, "");
    return fromApi || fromBrand;
  }, [pricing]);

  const shoppexPlanUrls = useMemo(() => {
    const map = new Map();
    for (const entry of pricing?.shoppex_plans || []) {
      if (entry.plan_id && entry.url) {
        map.set(entry.plan_id, entry.url);
      }
    }
    return map;
  }, [pricing]);

  const shoppexPaymentLabel = useMemo(
    () => shoppexPayments.map((item) => item.label).join(", "),
    [shoppexPayments],
  );

  const discordPaymentLabel = useMemo(
    () => discordTicketPayments.map((item) => item.label).join(", "),
    [discordTicketPayments],
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
        setError(`${caught.message} Use the store or Discord instead.`);
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
                shoppexUrl={resolvePlanStoreUrl(plan, shoppexPlanUrls, shoppexStoreUrl)}
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
                shoppexUrl={resolvePlanStoreUrl(plan, shoppexPlanUrls, shoppexStoreUrl)}
              />
            ))}
          </div>
        </>
      ) : null}

      <div className="pricing-cta">
        <h3>Payment options</h3>
        <p>
          {shoppexStoreUrl
            ? `Buy directly on our store with ${shoppexPaymentLabel || "crypto or PayPal"}. At checkout, click **Connect Discord** — do not type your ID manually.`
            : "Store checkout is being finalized. Join Discord for manual payment options in the meantime."}
        </p>

        <div className="pricing-payment-grid">
          <PaymentMethodList title="Store checkout" methods={shoppexPayments} />
          <PaymentMethodList title="Discord ticket only" methods={discordTicketPayments} />
        </div>

        <div className="pricing-cta__actions">
          {shoppexStoreUrl ? (
            <a className="btn btn--primary" href={shoppexStoreUrl} target="_blank" rel="noreferrer">
              Open store
            </a>
          ) : null}
          <a className="btn btn--discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
            <IconDiscord size={18} />
            Join Discord for {discordPaymentLabel || "Ethereum, Paysafe, or Discord pay"}
          </a>
        </div>
      </div>

      <p className="muted pricing-footnote">
        Card checkout{stripeEnabled ? "" : " (coming soon)"} via Stripe. Store accepts crypto and PayPal Friends &amp; Family.
        For {discordPaymentLabel || "Ethereum, Greek Paysafe, or Discord payment"}, open a purchase ticket in Discord.
      </p>
    </LegalDocument>
  );
}
