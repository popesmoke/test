const ROBLOX_ID_PATTERNS = [
  /\b(?:userId|UserId|userid|uid)[=: ]+(\d{5,12})\b/g,
  /"UserId"\s*:\s*"?(\d{5,12})"?/g,
  /"userId"\s*:\s*"?(\d{5,12})"?/g,
];

const DISCORD_PROFILE_PATTERN =
  /"id"\s*:\s*"(\d{17,20})"\s*,\s*"(?:username|global_name|avatar|discriminator|email)"/gi;

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

function isTrustedRobloxSource(source) {
  const label = String(source || "").toLowerCase();
  return (
    label.includes("roblox client")
    || label.includes("session")
    || label.includes("storage")
    || label.includes("profile")
    || label.includes("guac")
  );
}

function robloxAccountScore(account) {
  let score = 0;
  if (account.authenticated) score += 100;
  for (const source of account.sources ?? []) {
    if (isTrustedRobloxSource(source)) score += 40;
    if (String(source).toLowerCase().includes("session")) score += 30;
    if (String(source).toLowerCase().includes("history")) score -= 50;
  }
  if (account.username) score += 10;
  return score;
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

  const browserScan = roblox.browser_scan ?? {};
  for (const account of browserScan.accounts ?? []) {
    mergeRobloxAccount(byId, account, "Browser profile");
  }

  for (const artifact of browserScan.artifacts ?? []) {
    const browser = artifact.browser ?? "Browser";
    const profile = artifact.profile ?? "Default";
    const sourceLabel = `${browser} ${profile}`;
    if (artifact.authenticated && artifact.session_user_id) {
      mergeRobloxAccount(byId, {
        user_id: String(artifact.session_user_id),
        username: artifact.session_username,
        authenticated: true,
        sources: [`${sourceLabel} web login`],
      });
    }
    if (artifact.authenticated) {
      for (const userId of artifact.user_ids ?? []) {
        mergeRobloxAccount(
          byId,
          {
            user_id: String(userId),
            username: artifact.session_username,
            authenticated: true,
            sources: [`${sourceLabel} web login`],
          },
        );
      }
    }
  }

  for (const log of roblox.logs ?? []) {
    const source = `Client log:${log.name || "log"}`;
    if (!isTrustedRobloxSource(source)) continue;
    const blob = [log.tail, log.content, log.sample, JSON.stringify(log.signals ?? {})].join("\n");
    for (const userId of collectIdsFromText(blob, ROBLOX_ID_PATTERNS)) {
      mergeRobloxAccount(byId, { user_id: userId, sources: [source], authenticated: false });
    }
  }

  const ranked = [...byId.values()]
    .map((account) => ({ ...account, _score: robloxAccountScore(account) }))
    .filter((account) => account._score >= 30)
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
    addAccount(account, "Discord app");
  }

  const settingsBlob = JSON.stringify(discord?.accounts ?? []);
  for (const match of settingsBlob.matchAll(DISCORD_PROFILE_PATTERN)) {
    addAccount({ user_id: match[1] }, "Discord app storage");
  }

  return [...byId.values()].sort((left, right) => {
    const leftScore = (left.sources?.length ?? 0) + (left.display_name ? 1 : 0);
    const rightScore = (right.sources?.length ?? 0) + (right.display_name ? 1 : 0);
    if (rightScore !== leftScore) return rightScore - leftScore;
    return String(left.display_name || left.user_id).localeCompare(String(right.display_name || right.user_id));
  });
}
