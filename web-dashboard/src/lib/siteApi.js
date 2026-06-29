import { API_URL } from "../config/brand.js";

export async function fetchSiteConfig() {
  const response = await fetch(`${API_URL}/site/config`);
  if (!response.ok) return { demo_video_url: "", stripe_enabled: false };
  return response.json();
}

export async function fetchPricing() {
  const response = await fetch(`${API_URL}/site/pricing`);
  if (!response.ok) throw new Error("Could not load pricing");
  return response.json();
}

export async function fetchChangelog() {
  const response = await fetch(`${API_URL}/site/changelog`);
  if (!response.ok) return [];
  return response.json();
}

export async function fetchSiteAlerts() {
  const response = await fetch(`${API_URL}/site/alerts`);
  if (!response.ok) return [];
  return response.json();
}

export async function createCheckoutSession(token, planId) {
  const response = await fetch(`${API_URL}/checkout/create-session`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ plan_id: planId }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.message || data.detail || "Checkout failed");
    error.code = data.detail;
    throw error;
  }
  return data;
}
