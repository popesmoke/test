const ROBLOX_ID_PATTERNS = [
  /\b(?:userId|UserId|userid|uid)[=: ]+(\d{5,12})\b/g,
  /"UserId"\s*:\s*"?(\d{5,12})"?/g,
  /"userId"\s*:\s*"?(\d{5,12})"?/g,
  /"id"\s*:\s*"?(\d{5,12})"?/g,
];

const DISCORD_PROFILE_PATTERN =
  /"id"\s*:\s*"(\d{17,20})"\s*,\s*"(?:username|global_name|avatar|discriminator|email)"/gi;

const DISCORD_ID_PATTERNS = [
  /"id"\s*:\s*"(\d{17,20})"/g,
  /"user_id"\s*:\s*"(\d{17,20})"/gi,
  /"currentUserId"\s*:\s*"(\d{17,20})"/gi,
  /"current_user_id"\s*:\s*"(\d{17,20})"/gi,
  /"remote_id"\s*:\s*"(\d{17,20})"/gi,
];

const DISCORD_TOKEN_PATTERN =
  /(mfa\.[A-Za-z0-9_-]{20,}|[MN][A-Za-z0-9_-]{23,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{25,})/gi;

function discordUserIdFromToken(token) {
  const part = String(token || "").split(".")[0];
  if (!part) return null;
  const padding = "=".repeat((4 - (part.length % 4)) % 4);
  try {
    const decoded = atob(part + padding);
    return isPlausibleDiscordId(decoded) ? decoded : null;
  } catch {
    return null;
  }
}

function collectDiscordIdsFromText(text) {
  const ids = new Set(collectIdsFromText(text, DISCORD_ID_PATTERNS));
  const value = String(text || "");
  DISCORD_TOKEN_PATTERN.lastIndex = 0;
  for (const match of value.matchAll(DISCORD_TOKEN_PATTERN)) {
    const userId = discordUserIdFromToken(match[1]);
    if (userId) ids.add(userId);
  }
  return ids;
}

function collectIdsFromText(text, patterns) {
  const ids = new Set();
  const value = String(text || "");
  for (const pattern of patterns) {
    pattern.lastIndex = 0;
    for (const match of value.matchAll(pattern)) {
      const id = String(match[1] || "").trim();
      if (id) ids.add(id);
    }
  }
  return ids;
}

function isPlausibleRobloxId(userId) {
  const id = String(userId || "").trim();
  if (!/^\d{5,12}$/.test(id)) return false;
  const numeric = Number(id);
  return Number.isFinite(numeric) && numeric > 0;
}

function isPlausibleDiscordId(userId) {
  if (!/^\d{17,20}$/.test(userId)) return false;
  try {
    const value = BigInt(userId);
    const discordEpoch = 1_420_070_400_000n;
    const timestamp = (value >> 22n) + discordEpoch;
    const now = BigInt(Date.now());
    return timestamp >= discordEpoch && timestamp <= now + 86_400_000n;
  } catch {
    return false;
  }
}

function isTrustedRobloxSource(source) {
  const label = String(source || "").toLowerCase();
  return (
    label.includes("roblox client")
    || label.includes("roblox profile")
    || label.includes("account switcher")
    || label.includes("session")
    || label.includes("storage")
    || label.includes("profile")
    || label.includes("guac")
    || label.includes("web login")
  );
}

function robloxAccountScore(account) {
  let score = 0;
  if (account.authenticated) score += 200;
  if (account.username) score += 20;
  for (const source of account.sources ?? []) {
    const label = String(source).toLowerCase();
    if (isTrustedRobloxSource(source)) score += 40;
    if (label.includes("account switcher")) score += 80;
    if (label.includes("web login")) score += 55;
    if (label.includes("session")) score += 30;
    if (label.includes("history")) score -= 100;
    if (label.includes("client log")) score -= 80;
    if (label.includes("edge default") || label.includes("chrome default")) score -= 40;
  }
  return score;
}

function mergeRobloxAccount(map, account, sourceLabel) {
  const userId = account?.user_id ? String(account.user_id) : "";
  if (!userId || !isPlausibleRobloxId(userId)) return;
  const existing = map.get(userId) ?? {
    user_id: userId,
    username: null,
    headshot_url: null,
    sources: [],
    authenticated: false,
  };
  if (account.username) existing.username = account.username;
  if (account.headshot_url) existing.headshot_url = account.headshot_url;
  if (account.authenticated) existing.authenticated = true;
  const sources = account.sources?.length ? account.sources : sourceLabel ? [sourceLabel] : [];
  if (sources.length) {
    existing.sources = [...new Set([...existing.sources, ...sources])];
  }
  map.set(userId, existing);
}

export function collectRobloxAccountsFromReport(roblox) {
  const byId = new Map();
  if (!roblox || typeof roblox !== "object") return [];

  for (const account of roblox.accounts ?? []) {
    mergeRobloxAccount(byId, account);
  }

  const browserScan = roblox.browser_scan ?? {};
  for (const account of browserScan.accounts ?? []) {
    mergeRobloxAccount(byId, account, "Browser profile");
  }

  for (const artifact of browserScan.artifacts ?? []) {
    const browser = artifact.browser ?? "Browser";
    const profile = artifact.profile ?? "Default";
    const sourceLabel = `${browser} ${profile}`;
    if (!artifact.authenticated) continue;
    const sessionIds = new Set();
    for (const userId of artifact.session_user_ids ?? []) {
      if (userId) sessionIds.add(String(userId));
    }
    if (artifact.session_user_id) {
      sessionIds.add(String(artifact.session_user_id));
    }
    for (const userId of sessionIds) {
      mergeRobloxAccount(byId, {
        user_id: userId,
        username: artifact.session_username,
        authenticated: true,
        sources: [`${sourceLabel} web login`],
      });
    }
  }

  const ranked = [...byId.values()]
    .map((account) => ({ ...account, _score: robloxAccountScore(account) }))
    .filter((account) => account.authenticated && account._score >= 180)
    .sort((left, right) => {
      if (right._score !== left._score) return right._score - left._score;
      const leftId = Number(left.user_id);
      const rightId = Number(right.user_id);
      if (Number.isFinite(leftId) && Number.isFinite(rightId)) return leftId - rightId;
      return String(left.user_id).localeCompare(String(right.user_id));
    });

  return ranked.map(({ _score, ...account }) => account);
}

export function collectDiscordAccountsFromReport(discord, report) {
  const byId = new Map();

  const addAccount = (account, sourceLabel) => {
    const userId = String(account?.user_id || "").trim();
    if (!userId || !isPlausibleDiscordId(userId)) return;
    const existing = byId.get(userId) ?? {
      user_id: userId,
      display_name: null,
      avatar_hash: null,
      sources: [],
    };
    if (account.display_name && !existing.display_name) existing.display_name = account.display_name;
    if (account.avatar_hash && !existing.avatar_hash) existing.avatar_hash = account.avatar_hash;
    if (account.avatar_url && !existing.avatar_url) existing.avatar_url = account.avatar_url;
    if (sourceLabel) {
      existing.sources = [...new Set([...(existing.sources ?? []), sourceLabel])];
    }
    byId.set(userId, existing);
  };

  for (const account of discord?.accounts ?? []) {
    const displayName = account.display_name;
    addAccount(
      {
        ...account,
        display_name:
          displayName && !String(displayName).startsWith("User ")
            ? displayName
            : null,
      },
      "Discord app",
    );
  }

  for (const userId of discord?.aggregate_user_ids ?? []) {
    addAccount({ user_id: String(userId) }, "Discord app");
  }

  const settingsBlob = JSON.stringify(discord ?? {});
  for (const match of settingsBlob.matchAll(DISCORD_PROFILE_PATTERN)) {
    addAccount({ user_id: match[1] }, "Discord app storage");
  }
  for (const userId of collectDiscordIdsFromText(settingsBlob)) {
    addAccount({ user_id: userId }, "Discord app storage");
  }

  for (const hint of discord?.browser_hints ?? []) {
    addAccount(
      {
        user_id: hint.user_id,
        display_name: hint.display_name,
      },
      hint.source ? `${hint.source} web login` : "Browser profile",
    );
  }

  const diagnosticsBlob = JSON.stringify(report?.application_diagnostics?.discord ?? {});
  for (const userId of collectDiscordIdsFromText(diagnosticsBlob)) {
    addAccount({ user_id: userId }, "Discord app data");
  }

  return [...byId.values()].sort((left, right) => {
    const leftScore = (left.sources?.length ?? 0) + (left.display_name ? 1 : 0);
    const rightScore = (right.sources?.length ?? 0) + (right.display_name ? 1 : 0);
    if (rightScore !== leftScore) return rightScore - leftScore;
    return String(left.display_name || left.user_id).localeCompare(String(right.display_name || right.user_id));
  });
}
