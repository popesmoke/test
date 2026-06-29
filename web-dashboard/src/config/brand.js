export const API_URL = import.meta.env.VITE_API_URL || "https://virello-secure.onrender.com";
export const BRAND_LOGO = "/assets/virello-scanner-logo.png";
export const BRAND_NAME = "Virello";
export const BRAND_FULL = "Virello Secure";
export const DISCORD_INVITE_URL = import.meta.env.VITE_DISCORD_INVITE_URL || "https://discord.gg/wPZXKaPyWY";
export const SHOPPEX_STORE_URL = import.meta.env.VITE_SHOPPEX_STORE_URL || "https://officialvirello.myshoppex.io";
export const SCANNER_DOWNLOAD_URL = import.meta.env.VITE_SCANNER_DOWNLOAD_URL || "";
export const DEMO_VIDEO_URL = import.meta.env.VITE_DEMO_VIDEO_URL || "";

export const NAV_LINKS = [
  { to: "/", label: "Home" },
  { to: "/download", label: "Download" },
  { to: "/purchase", label: "Pricing" },
  { to: "/changelog", label: "Changelog" },
  { to: "/faq", label: "FAQ" },
  { to: "/about", label: "About" },
  { to: "/workspace", label: "Console" },
];

export const FOOTER_LINKS = [
  { to: "/privacy", label: "Privacy" },
  { to: "/tos", label: "Terms" },
  { to: "/faq", label: "FAQ" },
  { to: "/purchase", label: "Pricing" },
  { to: "/changelog", label: "Changelog" },
  { to: "/about", label: "About" },
  { to: "/download", label: "Download" },
];
