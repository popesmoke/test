import React from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import {
  BRAND_FULL,
  BRAND_LOGO,
  BRAND_TAGLINE,
  DISCORD_INVITE_URL,
  FOOTER_LINKS,
  NAV_LINKS,
} from "../config/brand.js";
import { IconDiscord } from "./VirelloIcons.jsx";

export function SiteLayout({ children, variant = "default" }) {
  const content = children ?? <Outlet />;

  return (
    <div className={`site ${variant === "minimal" ? "site--minimal" : ""}`}>
      <header className="site-header">
        <div className="site-header__inner">
          <Link to="/" className="site-brand">
            <img src={BRAND_LOGO} alt={BRAND_FULL} className="site-brand__logo" />
            <div className="site-brand__text">
              <span className="site-brand__name">{BRAND_FULL}</span>
              <span className="site-brand__tag">{BRAND_TAGLINE}</span>
            </div>
          </Link>

          <nav className="site-nav" aria-label="Primary">
            {NAV_LINKS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `site-nav__link${isActive ? " site-nav__link--active" : ""}`}
                end={item.to === "/"}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="site-header__actions">
            <a
              className="btn btn--ghost btn--sm"
              href={DISCORD_INVITE_URL}
              target="_blank"
              rel="noreferrer"
              title="Join Virello Discord"
            >
              <IconDiscord size={16} />
              <span>Discord</span>
            </a>
            <Link to="/workspace" className="btn btn--primary btn--sm">
              Console
            </Link>
          </div>
        </div>
      </header>

      <main className="site-main">{content}</main>

      <footer className="site-footer">
        <div className="site-footer__inner">
          <div className="site-footer__brand">
            <img src={BRAND_LOGO} alt="" className="site-footer__logo" />
            <div>
              <strong>{BRAND_FULL}</strong>
              <p>Consent-first Roblox diagnostic scans for reviewers and support teams.</p>
            </div>
          </div>

          <div className="site-footer__links">
            {FOOTER_LINKS.map((item) => (
              <Link key={item.to} to={item.to}>
                {item.label}
              </Link>
            ))}
            <a href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
              Discord
            </a>
          </div>

          <p className="site-footer__copy">
            &copy; {new Date().getFullYear()} Virello. All rights reserved.{" "}
            <a href="https://icons8.com" target="_blank" rel="noreferrer">
              Icons by Icons8
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
