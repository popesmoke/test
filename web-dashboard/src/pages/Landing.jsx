import React, { useState } from "react";
import { Link } from "react-router-dom";
import { MaterialIcon } from "../components/MaterialIcon.jsx";
import { Reveal } from "../components/Reveal.jsx";
import { IconDiscord, IconDownload } from "../components/VirelloIcons.jsx";

const ICON_ACCENT = "ff4d5f";
const ICON_SOFT = "ff8d9a";

const STEPS = [
  {
    num: "01",
    title: "Create a PIN",
    body: "Sign in to the review console and generate a session PIN. Share it with the user during screenshare.",
    icon: "console",
  },
  {
    num: "02",
    title: "User runs the scanner",
    body: "The user downloads the Windows app, enters your PIN, and reviews the consent summary before starting.",
    icon: "download",
  },
  {
    num: "03",
    title: "Scan completes",
    body: "The scanner runs on the user's PC and uploads results to your session. Most scans finish in about two minutes.",
    icon: "timer",
  },
  {
    num: "04",
    title: "Review the report",
    body: "Results appear in your console with a clear summary and ranked findings you can walk through live.",
    icon: "report",
  },
];

const CAPABILITIES = [
  {
    title: "Built for live reviews",
    body: "Designed for screenshare workflows where you need fast answers and a report you can explain on the spot.",
    icon: "verified",
    wide: true,
  },
  {
    title: "Consent before upload",
    body: "Users see what will be collected and must approve before anything leaves their machine.",
    icon: "consent",
  },
  {
    title: "Structured results",
    body: "Findings arrive ranked and grouped so your team can reach a verdict without digging through raw data.",
    icon: "list_checks",
  },
  {
    title: "Your rules",
    body: "Configure watch lists and review settings that match how your team handles cases.",
    icon: "lock",
  },
];

const STATS = [
  { value: "~2 min", label: "Typical scan time", icon: "timer" },
  { value: "PIN", label: "Links scan to your session", icon: "pin" },
  { value: "Win 10+", label: "Desktop scanner", icon: "windows" },
  { value: "0", label: "Accounts needed for scanned users", icon: "users" },
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
      <section className="hero hero--asymmetric">
        <Reveal className="hero__content">
          <p className="hero__eyebrow anim-fade-down">Windows screenshare reviews</p>
          <h1 className="anim-fade-up">
            PC scans built for
            <span className="hero__accent"> live reviews</span>
          </h1>
          <p className="hero__lead anim-fade-up anim-delay-1">
            The user approves the scan. You get a clear report in the review console.
          </p>
          <div className="hero__actions anim-fade-up anim-delay-2">
            <Link to="/download" className="btn btn--primary btn--lg">
              <MaterialIcon name="download" size={18} color="ffffff" />
              Download scanner
            </Link>
            <Link to="/purchase" className="btn btn--outline btn--lg">
              View pricing
            </Link>
            <Link to="/workspace" className="btn btn--ghost btn--lg">
              Open console
            </Link>
          </div>
          <ul className="hero__trust anim-fade-up anim-delay-3">
            <li>Consent before upload</li>
            <li>Watch lists you control</li>
            <li>Most scans take about 2 minutes</li>
          </ul>
        </Reveal>

        <Reveal className="hero__panel" delay={120}>
          <div className="hero__panel-inner">
            <div className="hero__stat hero__stat--highlight">
              <MaterialIcon name="timer" size={22} color={ICON_SOFT} />
              <span className="hero__stat-value">~2 min</span>
              <span className="hero__stat-label">Typical scan time</span>
            </div>
            <div className="hero__stat">
              <MaterialIcon name="pin" size={20} color={ICON_SOFT} />
              <span className="hero__stat-value">PIN</span>
              <span className="hero__stat-label">Links the scan to your console session</span>
            </div>
            <div className="hero__stat">
              <MaterialIcon name="windows" size={20} color={ICON_SOFT} />
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
            <Reveal key={stat.label} className="stat-block" delay={i * 70}>
              <MaterialIcon name={stat.icon} size={20} color={ICON_SOFT} className="stat-block__icon" />
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
          {STEPS.map((step, i) => (
            <Reveal key={step.num} as="li" className="step-card" delay={i * 90}>
              <div className="step-card__icon">
                <MaterialIcon name={step.icon} size={22} color={ICON_ACCENT} />
              </div>
              <div className="step-card__body">
                <span className="step-card__num">{step.num}</span>
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
              delay={i * 80}
            >
              <div className="feature-card__icon">
                <MaterialIcon name={item.icon} size={24} color={ICON_ACCENT} />
              </div>
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
            <Reveal key={item.q} delay={i * 60}>
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
            <MaterialIcon name="download" size={16} color="ffffff" />
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
