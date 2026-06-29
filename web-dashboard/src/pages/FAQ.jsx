import React from "react";
import { DISCORD_INVITE_URL } from "../config/brand.js";
import { IconDiscord } from "../components/VirelloIcons.jsx";
import { LegalArticle, LegalDocument } from "../components/LegalPage.jsx";

const FAQ_ITEMS = [
  {
    q: "Is Virello a virus?",
    a: "No. Virello is a consent-based diagnostic scanner for Roblox screenshare reviews. It reads local system activity records (program runs, downloads, account hints) and sends a structured report to your reviewer. It does not steal passwords, Roblox cookies, Discord tokens, or message contents.",
  },
  {
    q: "Why does my antivirus flag it?",
    a: "Security tools often flag new or uncommon executables, especially tools that inspect other programs. That is a reputation warning, not proof the scanner is malicious. Virello is built for transparency: you choose when to run it, you see what is collected, and the reviewer gets a report you agreed to share.",
  },
  {
    q: "Why are there false detections?",
    a: "No scanner is perfect. Virello uses multiple signals before flagging something serious. A single odd file name or old download may show as a low concern while multiple matching traces raise the score. Reviewers should read the full report, not just one line.",
  },
  {
    q: "Why use Virello instead of manual checking?",
    a: "Manual checking is slow and easy to miss deleted programs, old downloads, or switched accounts. Virello gathers related traces in one place so reviews are faster, more consistent, and easier to explain to the person being checked.",
  },
  {
    q: "What does the scanner actually collect?",
    a: "Program activity hints, download history, Roblox and Discord account IDs found locally, and security-related warning signs. It does not upload your full hard drive, browser history text, or private messages.",
  },
  {
    q: "How do I get access?",
    a: "Buy on our Shoppex store with Bitcoin, Litecoin, USDT, Solana, or PayPal Friends & Family. At checkout, click Connect Discord and authorize — your reviewer role is granted automatically after payment. For Ethereum, Greek Paysafe, or Discord payment, join the server and open a purchase ticket.",
  },
  {
    q: "Who can see my scan results?",
    a: "Only people with your PIN session and reviewer access. Scans are not posted publicly.",
  },
];

export function FAQPage() {
  return (
    <LegalDocument badge="FAQ" title="Common questions" updated="June 2026">
      <p className="legal-doc__lead">
        Straight answers about safety, detections, and how Virello works.
      </p>

      {FAQ_ITEMS.map((item, index) => (
        <LegalArticle key={item.q} index={String(index + 1)} title={item.q}>
          <p>{item.a}</p>
        </LegalArticle>
      ))}

      <LegalArticle index="+" title="Still have questions?">
        <p>Join our Discord and open a support lane. Staff can walk you through setup, licensing, and scan results.</p>
        <a className="btn btn--discord" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
          <IconDiscord size={18} />
          Join Virello Discord
        </a>
      </LegalArticle>
    </LegalDocument>
  );
}
