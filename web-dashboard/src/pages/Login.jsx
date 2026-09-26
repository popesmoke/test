import React from "react";
import { Link, Navigate } from "react-router-dom";
import "../marketing.css";
import { BRAND_FULL, BRAND_LOGO, DISCORD_INVITE_URL } from "../config/brand.js";
import { IconDiscord } from "../components/VirelloIcons.jsx";
import { getStoredToken, startDiscordLogin } from "../lib/auth.js";

export function LoginPage({ loginError }) {
  const token = getStoredToken();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(loginError || "");

  React.useEffect(() => {
    setError(loginError || "");
  }, [loginError]);

  if (token) {
    return <Navigate to="/workspace" replace />;
  }

  async function handleDiscordLogin() {
    setError("");
    setBusy(true);
    try {
      await startDiscordLogin("/workspace");
    } catch (caught) {
      setError(caught.message || "Could not reach the authentication server.");
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card auth-card--enter">
        <div className="auth-card__brand">
          <Link to="/">
            <img src={BRAND_LOGO} alt={BRAND_FULL} />
          </Link>
          <h1>Review Console</h1>
          <p>Sign in with Discord to create PIN sessions and review completed scans.</p>
        </div>

        <div className="auth-card__body">
          {error ? <p className="error" role="alert">{error}</p> : null}
          <div className="auth-card__notice">
            <p>
              You need the <strong>Access</strong> role in our Discord server to generate PINs and view reports.
            </p>
          </div>
          <a className="auth-discord-link" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
            <IconDiscord size={16} />
            Need access? Join Discord
          </a>
          <button className="btn btn--discord btn--lg" type="button" onClick={handleDiscordLogin} disabled={busy}>
            <IconDiscord size={18} />
            {busy ? "Connecting…" : "Continue with Discord"}
          </button>
        </div>
      </div>
    </div>
  );
}
