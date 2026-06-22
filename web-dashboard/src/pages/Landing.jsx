import React from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  CheckCircle2,
  Clock3,
  Fingerprint,
  MessageCircle,
  ScanSearch,
  Shield,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { DISCORD_INVITE_URL } from "../config/brand.js";

const FEATURES = [
  {
    icon: ScanSearch,
    title: "Deep Forensic Scanning",
    text: "Multi-layer analysis across execution traces, filesystem artifacts, Roblox runtime signals, and cross-source correlation.",
  },
  {
    icon: ShieldCheck,
    title: "Low False Positives",
    text: "Evidence is scored by reliability tier. Weak signals require corroboration before they affect your verdict.",
  },
  {
    icon: Clock3,
    title: "Fast, Bounded Scans",
    text: "Primary results are delivered within six minutes. Long-running collectors continue safely in the background.",
  },
  {
    icon: Fingerprint,
    title: "Consent-First Design",
    text: "Users explicitly approve collection. No passwords, session cookies, or message contents are ever gathered.",
  },
  {
    icon: Activity,
    title: "Structured Review Console",
    text: "Plain-language summaries for quick decisions, plus an advanced reviewer mode for full forensic detail.",
  },
  {
    icon: Zap,
    title: "Production-Grade Stability",
    text: "Built for long sessions, repeated scans, and real support workflows — not one-off demos.",
  },
];

const STEPS = [
  { num: "01", title: "Generate a PIN", text: "Sign in with Discord, verify your Access role, and create a session PIN." },
  { num: "02", title: "Run the desktop scanner", text: "The user enters the PIN, reviews consent, and starts a diagnostic scan on their device." },
  { num: "03", title: "Review results", text: "Completed scans appear in your console with evidence chains, activity timelines, and verdict tools." },
];

export function LandingPage() {
  return (
    <div className="landing">
      <section className="hero">
        <div className="hero__content">
          <p className="hero__eyebrow">Roblox Screenshare & Diagnostic Platform</p>
          <h1>
            Clear evidence.
            <br />
            <span className="hero__accent">Confident decisions.</span>
          </h1>
          <p className="hero__lead">
            Virello Secure helps reviewers verify Roblox executor risk with structured forensic scans,
            calibrated confidence scoring, and a professional review workflow.
          </p>
          <div className="hero__actions">
            <Link to="/workspace" className="primary hero__cta">
              <Shield size={18} />
              Open Review Console
            </Link>
            <a className="hero__discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
              <MessageCircle size={18} />
              Join Discord
            </a>
          </div>
          <ul className="hero__trust">
            <li>
              <CheckCircle2 size={16} /> Consent-based collection
            </li>
            <li>
              <CheckCircle2 size={16} /> 29+ tracked executor brands
            </li>
            <li>
              <CheckCircle2 size={16} /> 6-minute scan budget
            </li>
          </ul>
        </div>
        <div className="hero__panel">
          <div className="hero__panel-inner">
            <div className="hero__stat">
              <span className="hero__stat-value">6 min</span>
              <span className="hero__stat-label">Primary scan delivery</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">29+</span>
              <span className="hero__stat-label">Executor brands tracked</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">15+</span>
              <span className="hero__stat-label">Forensic artifact sources</span>
            </div>
            <div className="hero__stat">
              <span className="hero__stat-value">0</span>
              <span className="hero__stat-label">Session cookies collected</span>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <header className="section__header">
          <p className="section__eyebrow">Capabilities</p>
          <h2>Built for real screenshare workflows</h2>
          <p>Every layer is designed for accuracy, clarity, and speed — without sacrificing reviewer trust.</p>
        </header>
        <div className="feature-grid">
          {FEATURES.map((feature) => (
            <article key={feature.title} className="feature-card">
              <div className="feature-card__icon">
                <feature.icon size={22} />
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section section--alt">
        <header className="section__header">
          <p className="section__eyebrow">How it works</p>
          <h2>Three steps from PIN to verdict</h2>
        </header>
        <ol className="steps">
          {STEPS.map((step) => (
            <li key={step.num} className="step-card">
              <span className="step-card__num">{step.num}</span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="cta-band">
        <div>
          <h2>Ready to review with confidence?</h2>
          <p>Sign in with Discord to access the review console, or join our community for support and access.</p>
        </div>
        <div className="cta-band__actions">
          <Link to="/workspace" className="primary">
            Get Started
          </Link>
          <a href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer" className="cta-band__discord">
            <MessageCircle size={16} />
            Discord Server
          </a>
        </div>
      </section>
    </div>
  );
}
