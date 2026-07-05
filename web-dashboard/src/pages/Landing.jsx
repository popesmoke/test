import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Reveal } from "../components/Reveal.jsx";
import {
  IconConsent,
  IconConsole,
  IconDownload,
  IconLock,
  IconRadar,
  IconShieldMark,
  IconTarget,
  IconTimer,
} from "../components/VirelloIcons.jsx";

const STEPS = [
  {
    num: "01",
    title: "Create a PIN",
    body: "Sign in to the review console and generate a session PIN. Share it with the user during screenshare.",
    icon: IconConsole,
  },
  {
    num: "02",
    title: "User runs the scanner",
    body: "The user downloads the Windows app, enters your PIN, and reviews what will be collected before starting.",
    icon: IconDownload,
  },
  {
    num: "03",
    title: "Scan completes",
    body: "The scanner checks filesystem traces, browser history, Roblox artifacts, and executor signals. Most scans finish in about two minutes.",
    icon: IconRadar,
  },
  {
    num: "04",
    title: "Review the report",
    body: "Results appear in your console session with ranked findings, evidence tiers, and a clear verdict summary.",
    icon: IconShieldMark,
  },
];

const CAPABILITIES = [
  {
    title: "Executor detection",
    body: "Scans for Volt, Synapse, Solara, and other known executors across filesystem, registry, and process traces.",
    icon: IconTarget,
    wide: true,
  },
  {
    title: "Consent before upload",
    body: "Users see exactly what is collected and must approve before any data leaves their machine.",
    icon: IconConsent,
  },
  {
    title: "Structured evidence",
    body: "Findings are ranked by severity with linked artifacts. No vague scores or unexplained flags.",
    icon: IconShieldMark,
  },
  {
    title: "Watch lists you control",
    body: "Configure custom detection rules and watch lists that match how your team reviews cases.",
    icon: IconLock,
  },
];

const STATS = [
  { value: "~2 min", label: "Typical scan time" },
  { value: "PIN", label: "Links scan to your session" },
  { value: "Win 10+", label: "Desktop scanner" },
  { value: "0", label: "Accounts needed for scanned users" },
];

const FAQ = [
  {
    q: "Does the scanned user need an account?",
    a: "No. Only reviewers sign in with Discord. The user just runs the desktop scanner with the PIN you provide.",
  },
  {
    q: "What data does the scanner collect?",
    a: "Filesystem traces, Windows forensics, browser history, Roblox artifacts, and anti-bypass signals. No passwords, cookies, or message contents.",
  },
  {
    q: "How do I get console access?",
    a: "Purchase a license through our Discord server. Staff verify payment and assign the Access role to your account.",
  },
  {
    q: "Can I use this outside Roblox reviews?",
    a: "Virello is built for Roblox screenshare checks. The detection engine targets executor and exploit tooling common in that context.",
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
      <section className="hero hero--asymmetric">
        <div className="hero__glow" aria-hidden="true" />
        <Reveal className="hero__content">
          <p className="hero__eyebrow">Windows screenshare reviews</p>
          <h1>
            PC scans built for
            <span className="hero__accent"> live reviews</span>
          </h1>
          <p className="hero__lead">
            The user approves the scan. You get a ranked report in the review console. No guesswork, no hidden collection.
          </p>
          <div className="hero__actions">
            <Link to="/download" className="btn btn--primary btn--lg">
              <IconDownload size={18} />
              Download scanner
            </Link>
            <Link to="/purchase" className="btn btn--outline btn--lg">
              View pricing
            </Link>
            <Link to="/workspace" className="btn btn--ghost btn--lg">
              Open console
            </Link>
          </div>
          <ul className="hero__trust">
            <li>Consent before upload</li>
            <li>Watch lists you control</li>
            <li>Most scans take about 2 minutes</li>
          </ul>
        </Reveal>

        <Reveal className="hero__panel" delay={120}>
          <div className="hero__panel-inner">
            <div className="hero__stat hero__stat--highlight">
              <IconTimer size={22} />
              <span className="hero__stat-value">~2 min</span>
              <span className="hero__stat-label">Typical scan time</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">PIN</span>
              <span className="hero__stat-label">Links the scan to your console session</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">Win 10+</span>
              <span className="hero__stat-label">Windows desktop scanner</span>
            </div>
          </div>
          <p className="hero__panel-note muted">
            Reviewers sign in with Discord. Scanned users do not need an account.
          </p>
        </Reveal>
      </section>

      <section className="section section--stats" aria-label="Key metrics">
        <div className="stats-row">
          {STATS.map((stat, i) => (
            <Reveal key={stat.label} className="stat-block" delay={i * 60}>
              <span className="stat-block__value">{stat.value}</span>
              <span className="stat-block__label">{stat.label}</span>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="section" id="how-it-works">
        <Reveal className="section__header">
          <p className="section__eyebrow">How it works</p>
          <h2>From PIN to verdict in four steps</h2>
          <p>Everything runs through a single session. The user stays in control, and you get structured results.</p>
        </Reveal>

        <ol className="steps steps--numbered">
          {STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <Reveal key={step.num} as="li" className="step-card" delay={i * 80}>
                <div className="step-card__icon">
                  <Icon size={20} />
                </div>
                <div className="step-card__body">
                  <span className="step-card__num">{step.num}</span>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </div>
              </Reveal>
            );
          })}
        </ol>
      </section>

      <section className="section section--alt">
        <Reveal className="section__header section__header--left">
          <p className="section__eyebrow">Capabilities</p>
          <h2>What the scanner checks</h2>
          <p>Focused detection for Roblox screenshare reviews, with evidence you can actually explain.</p>
        </Reveal>

        <div className="feature-grid feature-grid--asymmetric">
          {CAPABILITIES.map((item, i) => {
            const Icon = item.icon;
            return (
              <Reveal
                key={item.title}
                className={`feature-card${item.wide ? " feature-card--wide" : ""}`}
                delay={i * 70}
              >
                <div className="feature-card__icon">
                  <Icon size={22} />
                </div>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </Reveal>
            );
          })}
        </div>
      </section>

      <section className="section" id="faq">
        <Reveal className="section__header">
          <p className="section__eyebrow">FAQ</p>
          <h2>Common questions</h2>
        </Reveal>

        <div className="faq-list">
          {FAQ.map((item, i) => (
            <Reveal key={item.q} delay={i * 50}>
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
          <h2>Ready to run your first scan?</h2>
          <p>Download the scanner, create a PIN in the console, and share it during screenshare.</p>
        </div>
        <div className="cta-band__actions">
          <Link to="/download" className="btn btn--primary">
            <IconDownload size={16} />
            Download
          </Link>
          <Link to="/workspace" className="btn btn--outline">
            Open console
          </Link>
        </div>
      </Reveal>
    </div>
  );
}
