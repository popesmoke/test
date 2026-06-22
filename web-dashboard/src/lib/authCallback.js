import { DISCORD_ERROR_MESSAGES, setStoredToken } from "./auth.js";

/** Process ?token= or ?discord_error= before React mounts so WorkspaceApp never races the redirect. */
export function consumeAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  const discordError = params.get("discord_error");

  if (token) {
    setStoredToken(token);
    const path = window.location.pathname.startsWith("/workspace") ? "/workspace" : "/workspace";
    window.history.replaceState({}, document.title, path);
    return { kind: "token" };
  }

  if (discordError) {
    const message = DISCORD_ERROR_MESSAGES[discordError] || "Discord login failed. Please try again.";
    window.history.replaceState({}, document.title, "/login");
    return { kind: "error", error: discordError, message };
  }

  return null;
}
