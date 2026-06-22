import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { MessageCircle, Shield } from "lucide-react";
import { BRAND_FULL, BRAND_LOGO, DISCORD_INVITE_URL } from "../config/brand.js";
import { getStoredToken, startDiscordLogin } from "../lib/auth.js";

export function LoginPage({ loginError }) {
  const token = getStoredToken();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(loginError || "");

  useEffect(() => {
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
      <div className="auth-card">
        <div className="auth-card__brand">
          <img src={BRAND_LOGO} alt={BRAND_FULL} />
          <h1>Review Console</h1>
          <p>Sign in with Discord to manage PIN sessions and review scan results.</p>
        </div>

        <div className="auth-card__body">
          {error ? <p className="error">{error}</p> : null}
          <div className="auth-card__notice">
            <Shield size={18} />
            <p>
              You need the <strong>Access</strong> role in our Discord server to generate PINs and
              view completed scans. You can still sign in to see next steps.
            </p>
          </div>
          <a className="auth-discord-link" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
            <MessageCircle size={16} />
            Need access? Join the Discord server
          </a>
          <button className="primary discord-login-button" type="button" onClick={handleDiscordLogin} disabled={busy}>
            <MessageCircle size={18} />
            {busy ? "Connecting to Discord..." : "Continue with Discord"}
          </button>
        </div>
      </div>
    </div>
  );
}
