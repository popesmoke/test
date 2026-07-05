import React, { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
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
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 8);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className={`site ${variant === "minimal" ? "site--minimal" : ""}`}>
      <header className={`site-header${scrolled ? " site-header--scrolled" : ""}`}>
        <div className="site-header__inner">
          <Link to="/" className="site-brand">
            <img src={BRAND_LOGO} alt={BRAND_FULL} className="site-brand__logo" />
            <div className="site-brand__text">
              <span className="site-brand__name">{BRAND_FULL}</span>
              <span className="site-brand__tag">{BRAND_TAGLINE}</span>
            </div>
          </Link>

          <button
            type="button"
            className="site-nav-toggle"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span />
            <span />
            <span />
          </button>

          <nav className={`site-nav${menuOpen ? " site-nav--open" : ""}`} aria-label="Primary">
            {NAV_LINKS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `site-nav__link${isActive ? " site-nav__link--active" : ""}`}
                end={item.to === "/"}
                onClick={() => setMenuOpen(false)}
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
          <div className="site-footer__top">
            <div className="site-footer__brand">
              <img src={BRAND_LOGO} alt="" className="site-footer__logo" />
              <div>
                <strong>{BRAND_FULL}</strong>
                <p>Consent-first Roblox diagnostic scans for reviewers and support teams.</p>
              </div>
            </div>

            <div className="site-footer__cols">
              <div className="site-footer__col">
                <span className="site-footer__col-title">Product</span>
                <Link to="/download">Download</Link>
                <Link to="/purchase">Pricing</Link>
                <Link to="/workspace">Review Console</Link>
              </div>
              <div className="site-footer__col">
                <span className="site-footer__col-title">Company</span>
                <Link to="/about">About</Link>
                <a href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
                  Discord
                </a>
              </div>
              <div className="site-footer__col">
                <span className="site-footer__col-title">Legal</span>
                {FOOTER_LINKS.filter((l) => l.to === "/privacy" || l.to === "/tos").map((item) => (
                  <Link key={item.to} to={item.to}>
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>

          <p className="site-footer__copy">
            &copy; {new Date().getFullYear()} Virello. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
