/** Common executor / cheat names reviewers search for with Ctrl+F or the in-page filter. */
export const EXECUTOR_SEARCH_TERMS = [
  "Potassium",
  "Solara",
  "Wave",
  "Volt",
  "Synapse",
  "Xeno",
  "Delta",
  "Cosmic",
  "Seliware",
  "SirHurt",
  "Serotonin",
  "Lumen",
  "Matcha",
  "Photon",
  "Codex",
  "MacSploit",
  "Opiumware",
  "Velocity",
  "Madium",
  "Vega",
  "executor",
  "inject",
  "script hub",
];

export function textMatchesSearch(text, query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return true;
  return String(text || "").toLowerCase().includes(q);
}
