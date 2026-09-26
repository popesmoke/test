import React, { useState } from "react";
import { Link } from "react-router-dom";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
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
    body: "They enter the PIN, review what the scan checks, and choose whether to continue.",
  },
  {
    num: "03",
    title: "Scan finishes",
    body: "The app examines selected local artifacts, then submits its report to the matching case.",
  },
  {
    num: "04",
    title: "Review the report",
    body: "Review each signal with its source and context. The report supports your judgment; it does not decide for you.",
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
    a: "The consent screen summarizes the collection. The scanner does not read saved passwords, browser cookies, or private messages, and it does not close browsers.",
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

function ReviewFlowPanel() {
  const steps = [
    { number: "01", title: "Review the request", detail: "The user sees the collection summary first.", icon: "fact_check", tag: "User controlled" },
    { number: "02", title: "Scan on the device", detail: "Selected system and Roblox artifacts are checked locally.", icon: "computer", tag: "Local analysis" },
    { number: "03", title: "Walk through evidence", detail: "The reviewer sees findings, sources, and context in one case.", icon: "manage_search", tag: "Human review" },
  ];

  return (
    <div className="review-flow" aria-label="How a review works">
      <div className="review-flow__head">
        <div>
          <p className="review-flow__eyebrow">A clear review process</p>
          <h2>From consent to context</h2>
        </div>
        <span className="review-flow__mark" aria-hidden="true"><MaterialIcon name="shield" size={18} /></span>
      </div>
      <ol className="review-flow__steps">
        {steps.map((step, index) => (
          <li className="review-flow__step" key={step.number} style={{ "--flow-order": index }}>
            <span className="review-flow__number">{step.number}</span>
            <span className="review-flow__icon" aria-hidden="true"><MaterialIcon name={step.icon} size={18} /></span>
            <span className="review-flow__copy">
              <strong>{step.title}</strong>
              <span>{step.detail}</span>
            </span>
            <span className="review-flow__tag">{step.tag}</span>
          </li>
        ))}
      </ol>
      <p className="review-flow__footnote">
        <MaterialIcon name="info" size={15} />
        A scan is evidence for a reviewer—not an automatic verdict.
      </p>
    </div>
  );
}

export function LandingPage() {
  const [openFaq, setOpenFaq] = useState(null);

  return (
    <div className="landing">
      <section className="hero hero--console" aria-label="Virello">
        <Reveal className="hero__content">
          <p className="hero__eyebrow">LOCAL-FIRST ROBLOX PC SCANNER</p>
          <h1>Evidence you can explain.</h1>
          <p className="hero__lead">
            Virello helps reviewer teams inspect Roblox-related PC evidence during a screenshare, with consent and context built into the process.
          </p>
          <div className="hero__actions">
            <Link to="/download" className="btn btn--primary btn--lg">
              Get the scanner
            </Link>
            <Link to="/workspace" className="btn btn--outline btn--lg">
              Reviewer console
            </Link>
          </div>
          <ul className="hero__trust">
            <li>
              <MaterialIcon name="check_circle" size={14} color={ICON_SOFT} />
              User approval before scanning
            </li>
            <li>
              <MaterialIcon name="visibility_off" size={14} color={ICON_SOFT} />
              No browser cookies or messages
            </li>
            <li>
              <MaterialIcon name="person_search" size={14} color={ICON_SOFT} />
              Human-reviewed findings
            </li>
          </ul>
        </Reveal>

        <Reveal className="hero__visual" delay={80}>
          <ReviewFlowPanel />
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
