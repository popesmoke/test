import React, { useState } from "react";
import { Link } from "react-router-dom";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { DashboardPreview } from "../components/DashboardPreview.jsx";
import { Reveal } from "../components/Reveal.jsx";

const ICON_SOFT = "9b9ba3";

const STEPS = [
  {
    num: "01",
    title: "Create a PIN",
    body: "Open the review console and generate a session PIN. Share it with the user during screenshare.",
  },
  {
    num: "02",
    title: "User runs the scanner",
    body: "They download the Windows app, enter your PIN, and approve the consent summary before anything is collected.",
  },
  {
    num: "03",
    title: "Scan finishes",
    body: "The scanner runs locally and uploads results to your session. Most checks complete in about two minutes.",
  },
  {
    num: "04",
    title: "Review the report",
    body: "Open the session in your console. Findings are ranked so you can walk through them live.",
  },
];

const CAPABILITIES = [
  {
    title: "Built for live reviews",
    body: "Made for screenshare workflows where you need a clear report you can explain on the call.",
    wide: true,
  },
  {
    title: "Consent before upload",
    body: "Users see what will be collected and must approve before anything leaves their PC.",
  },
  {
    title: "Structured results",
    body: "Findings arrive ranked and grouped so your team can reach a verdict without raw data dumps.",
  },
  {
    title: "Discord-gated access",
    body: "Console access is tied to a verified Discord role after license activation.",
  },
];

const FAQ = [
  {
    q: "Does the scanned user need an account?",
    a: "No. Only reviewers sign in with Discord. The user runs the desktop scanner with the PIN you provide.",
  },
  {
    q: "What data does the scanner collect?",
    a: "Only what is listed on the consent screen before the scan starts. Passwords, cookies, and private messages are never collected.",
  },
  {
    q: "How do I get console access?",
    a: "Join our Discord server and open a purchase lane. Staff verify payment and assign the Access role to your account.",
  },
  {
    q: "Who is Virello for?",
    a: "Roblox reviewers, moderators, and support teams running PC checks during screenshare or ticket reviews.",
  },
];

function FaqItem({ item, open, onToggle }) {
  return (
    <div className={`faq-item${open ? " faq-item--open" : ""}`}>
      <button type="button" className="faq-item__trigger" onClick={onToggle} aria-expanded={open}>
        <span>{item.q}</span>
        <span className="faq-item__icon" aria-hidden="true" />
      </button>
      <div className="faq-item__panel" hidden={!open}>
        <p>{item.a}</p>
      </div>
    </div>
  );
}

export function LandingPage() {
  const [openFaq, setOpenFaq] = useState(null);

  return (
    <div className="landing">
      <section className="hero hero--console" aria-label="Virello">
        <Reveal className="hero__content">
          <h1>
            Virello
            <span className="hero__accent"> Scanner</span>
          </h1>
          <p className="hero__lead">
            Consent-first PC checks for Roblox screenshare reviews — clear reports your team can trust.
          </p>
          <div className="hero__actions">
            <Link to="/download" className="btn btn--primary btn--lg">
              Download scanner
            </Link>
            <Link to="/workspace" className="btn btn--outline btn--lg">
              Open console
            </Link>
          </div>
          <ul className="hero__trust">
            <li>
              <MaterialIcon name="consent" size={14} color={ICON_SOFT} />
              Consent before upload
            </li>
            <li>
              <MaterialIcon name="timer" size={14} color={ICON_SOFT} />
              ~2 min typical scan
            </li>
            <li>
              <MaterialIcon name="shield" size={14} color={ICON_SOFT} />
              Discord-gated console
            </li>
          </ul>
        </Reveal>

        <Reveal className="hero__visual" delay={80}>
          <DashboardPreview />
        </Reveal>
      </section>

      <section className="section" id="how-it-works">
        <Reveal className="section__header">
          <p className="section__eyebrow">How it works</p>
          <h2>From PIN to verdict in four steps</h2>
          <p>One session links the desktop scan to your console. The user stays in control of consent.</p>
        </Reveal>

        <ol className="steps steps--numbered">
          {STEPS.map((step, i) => (
            <Reveal key={step.num} as="li" className="step-card" delay={i * 50}>
              <span className="step-card__num" aria-hidden="true">
                {step.num}
              </span>
              <div className="step-card__body">
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            </Reveal>
          ))}
        </ol>
      </section>

      <section className="section section--alt">
        <Reveal className="section__header section__header--left">
          <p className="section__eyebrow">Why Virello</p>
          <h2>Made for reviewer teams</h2>
          <p>Less setup, clearer outcomes, and a workflow that fits how screenshares actually run.</p>
        </Reveal>

        <div className="feature-grid feature-grid--asymmetric">
          {CAPABILITIES.map((item, i) => (
            <Reveal
              key={item.title}
              className={`feature-card${item.wide ? " feature-card--wide" : ""}`}
              delay={i * 40}
            >
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="section" id="faq">
        <Reveal className="section__header">
          <p className="section__eyebrow">FAQ</p>
          <h2>Common questions</h2>
        </Reveal>

        <div className="faq-list">
          {FAQ.map((item, i) => (
            <Reveal key={item.q} delay={i * 40}>
              <FaqItem
                item={item}
                open={openFaq === i}
                onToggle={() => setOpenFaq(openFaq === i ? null : i)}
              />
            </Reveal>
          ))}
        </div>
      </section>

      <Reveal className="cta-band">
        <div>
          <h2>Ready for your first scan?</h2>
          <p>Download the scanner, create a PIN, and share it during screenshare.</p>
        </div>
        <div className="cta-band__actions">
          <Link to="/download" className="btn btn--primary">
            Download
          </Link>
          <Link to="/purchase" className="btn btn--outline">
            View pricing
          </Link>
        </div>
      </Reveal>
    </div>
  );
}
