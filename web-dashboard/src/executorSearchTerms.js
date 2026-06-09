/** Common executor / cheat names reviewers search for with Ctrl+F or the in-page filter. */
export const EXECUTOR_SEARCH_TERMS = [
  "Codex",
  "Cosmic",
  "Delta",
  "DX9WARE",
  "Lumen",
  "MacSploit",
  "Madium",
  "Matcha",
  "Matrix Hub",
  "Opiumware",
  "Photon",
  "Potassium",
  "RbxCli",
  "Seliware",
  "Serotonin",
  "Severe",
  "SirHurt",
  "Solara",
  "Synapse",
  "Vega",
  "Velocity",
  "Volt",
  "Wave",
  "Xeno",
  "executor",
  "inject",
  "script hub",
];

export function textMatchesSearch(text, query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return true;
  return String(text || "").toLowerCase().includes(q);
}
