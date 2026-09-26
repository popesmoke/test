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
      <div className="auth-layout auth-layout--enter">
        <section className="auth-story" aria-labelledby="auth-story-title">
          <Link to="/" className="auth-story__brand">
            <img src={BRAND_LOGO} alt="" />
            <span>{BRAND_FULL}</span>
          </Link>
          <p className="auth-story__eyebrow">REVIEWER WORKSPACE</p>
          <h2 id="auth-story-title">A clear path from scan to review.</h2>
          <p className="auth-story__lead">Keep the session, evidence, and reviewer notes together in one case.</p>
          <ol className="auth-story__steps">
            <li><span>01</span><div><strong>Create a session PIN</strong><p>Share one code with the person running the scan.</p></div></li>
            <li><span>02</span><div><strong>Review the submitted evidence</strong><p>See why each item was included and where it came from.</p></div></li>
            <li><span>03</span><div><strong>Record your decision</strong><p>Make the final call with the context in front of you.</p></div></li>
          </ol>
          <Link className="auth-story__back" to="/">Back to Virello</Link>
        </section>

        <section className="auth-card auth-card--enter" aria-labelledby="login-title">
          <div className="auth-card__brand">
            <img src={BRAND_LOGO} alt="" />
            <p className="auth-card__eyebrow">SECURE SIGN IN</p>
            <h1 id="login-title">Reviewer console</h1>
            <p>Continue with the Discord account that has reviewer access.</p>
          </div>

          <div className="auth-card__body">
            {error ? <p className="error" role="alert">{error}</p> : null}
            <div className="auth-card__notice">
              <p>
                Your account needs the <strong>Access</strong> role in the Virello Discord server. This role is checked when you sign in.
              </p>
            </div>
            <button className="btn btn--discord btn--lg" type="button" onClick={handleDiscordLogin} disabled={busy}>
              <IconDiscord size={18} />
              {busy ? "Connecting to Discord…" : "Continue with Discord"}
            </button>
            <a className="auth-discord-link" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
              Need reviewer access? Join the server
            </a>
            <p className="auth-card__privacy">The scanned user does not need to create an account.</p>
          </div>
        </section>
      </div>
    </div>
  );
}
