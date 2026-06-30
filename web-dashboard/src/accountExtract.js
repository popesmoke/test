const ROBLOX_ID_PATTERNS = [
  /\b(?:userId|UserId|userid|uid)[=: ]+(\d{5,12})\b/g,
  /"UserId"\s*:\s*"?(\d{5,12})"?/g,
  /"userId"\s*:\s*"?(\d{5,12})"?/g,
  /roblox\.com\/users\/(\d{5,12})\b/gi,
];

const DISCORD_ID_PATTERN = /"(?:id|user_id|currentUserId|current_user_id|remote_id)"\s*:\s*"(\d{17,20})"/gi;

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

function mergeRobloxAccount(map, account, sourceLabel) {
  const userId = account?.user_id ? String(account.user_id) : "";
  if (!userId) return;
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

  for (const userId of roblox.aggregate_user_ids ?? []) {
    mergeRobloxAccount(byId, { user_id: String(userId), sources: ["Scan summary"] });
  }

  const browserScan = roblox.browser_scan ?? {};
  for (const account of browserScan.accounts ?? []) {
    mergeRobloxAccount(byId, account, "Browser profile");
  }

  for (const artifact of browserScan.artifacts ?? []) {
    for (const userId of artifact.user_ids ?? []) {
      mergeRobloxAccount(
        byId,
        {
          user_id: String(userId),
          username: artifact.session_username,
          authenticated: Boolean(artifact.authenticated),
          sources: artifact.sources,
        },
        `Browser: ${artifact.browser ?? "unknown"}`,
      );
    }
    if (artifact.session_user_id) {
      mergeRobloxAccount(byId, {
        user_id: String(artifact.session_user_id),
        username: artifact.session_username,
        authenticated: Boolean(artifact.authenticated),
        sources: artifact.sources,
      });
    }
  }

  for (const log of roblox.logs ?? []) {
    const blob = [log.tail, log.content, log.sample, JSON.stringify(log.signals ?? {})].join("\n");
    for (const userId of collectIdsFromText(blob, ROBLOX_ID_PATTERNS)) {
      mergeRobloxAccount(byId, { user_id: userId, sources: [`Client log:${log.name || "log"}`] });
    }
  }

  const scanBlob = JSON.stringify(browserScan.artifacts ?? []);
  for (const userId of collectIdsFromText(scanBlob, ROBLOX_ID_PATTERNS)) {
    mergeRobloxAccount(byId, { user_id: userId, sources: ["Browser artifact"] });
  }

  return [...byId.values()].sort((left, right) => {
    const leftId = Number(left.user_id);
    const rightId = Number(right.user_id);
    if (Number.isFinite(leftId) && Number.isFinite(rightId)) return leftId - rightId;
    return String(left.user_id).localeCompare(String(right.user_id));
  });
}

export function collectDiscordAccountsFromReport(discord, report) {
  const byId = new Map();

  const addAccount = (account) => {
    const userId = String(account?.user_id || "").trim();
    if (!userId || !isPlausibleDiscordId(userId)) return;
    const existing = byId.get(userId) ?? {
      user_id: userId,
      display_name: null,
      avatar_hash: null,
    };
    if (account.display_name && !existing.display_name) existing.display_name = account.display_name;
    if (account.avatar_hash && !existing.avatar_hash) existing.avatar_hash = account.avatar_hash;
    if (account.avatar_url && !existing.avatar_url) existing.avatar_url = account.avatar_url;
    byId.set(userId, existing);
  };

  for (const account of discord?.accounts ?? []) {
    addAccount(account);
  }

  const blob = JSON.stringify({
    discord,
    diagnostics: report?.application_diagnostics ?? {},
  });
  for (const match of blob.matchAll(DISCORD_ID_PATTERN)) {
    addAccount({ user_id: match[1] });
  }

  return [...byId.values()].sort((left, right) =>
    String(left.display_name || left.user_id).localeCompare(String(right.display_name || right.user_id)),
  );
}
