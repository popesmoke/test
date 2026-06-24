import { API_URL } from "../config/brand.js";

export function authHeaders(token) {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export const DISCORD_ERROR_MESSAGES = {
  discord_auth_failed: "Discord login failed. Please try again.",
  invalid_state: "Discord login expired. Please try again.",
  missing_code: "Discord did not return a login code. Please try again.",
  account_sharing_locked:
    "This Discord account was locked because it appears to be shared across multiple devices. Contact support to unlock it.",
};

export async function startDiscordLogin(returnPath = "/workspace") {
  const returnTo = `${window.location.origin}${returnPath}`;
  const response = await fetch(
    `${API_URL}/auth/discord/start?return_to=${encodeURIComponent(returnTo)}`,
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.url) {
    throw new Error(data.detail || "Could not start Discord login.");
  }
  window.location.assign(data.url);
}

export function getStoredToken() {
  return localStorage.getItem("checkerToken") ?? "";
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem("checkerToken", token);
  } else {
    localStorage.removeItem("checkerToken");
  }
}
