import React, { useEffect, useMemo, useState } from "react";
import { MaterialIcon } from "./components/MaterialIcon.jsx";
import { Pagination } from "./components/Pagination.jsx";
import {
  collectRobloxAccountsFromReport,
  collectDiscordAccountsFromReport,
} from "./accountExtract.js";
import { usePagination } from "./hooks/usePagination.js";

const API_URL = import.meta.env.VITE_API_URL || "https://virello-secure.onrender.com";

function PanelHeader({ icon, title }) {
  return (
    <header className="ws-panel__head">
      <MaterialIcon name={icon} size={20} />
      <div>
        <h4>{title}</h4>
      </div>
    </header>
  );
}

function robloxHeadshotUrl(account) {
  return account.headshot_url || null;
}

function discordAvatarUrl(account) {
  const userId = String(account.user_id || "");
  if (!userId) return null;
  const hash = account.avatar_hash;
  if (hash) return `https://cdn.discordapp.com/avatars/${userId}/${hash}.webp?size=128`;
  try {
    const avatarIndex = (BigInt(userId) >> 22n) % 6n;
    return `https://cdn.discordapp.com/embed/avatars/${avatarIndex}.png`;
  } catch {
    return null;
  }
}

export function AccountsTab({ report, token }) {
  const roblox = report.application_diagnostics?.roblox ?? {};
  const discord = report.application_diagnostics?.discord ?? {};
  const robloxAccounts = useMemo(() => collectRobloxAccountsFromReport(roblox), [roblox]);
  const discordAccounts = useMemo(
    () => collectDiscordAccountsFromReport(discord, report),
    [discord, report],
  );
  const [robloxProfiles, setRobloxProfiles] = useState({});
  const [discordProfiles, setDiscordProfiles] = useState({});

  const robloxPage = usePagination(robloxAccounts, 12);
  const discordPage = usePagination(discordAccounts, 12);

  const visibleRobloxIds = useMemo(
    () => robloxPage.slice.map((account) => account.user_id).filter(Boolean),
    [robloxPage.slice],
  );
  const visibleDiscordIds = useMemo(
    () => discordPage.slice.map((account) => account.user_id).filter(Boolean),
    [discordPage.slice],
  );

  useEffect(() => {
    if (!token || !visibleRobloxIds.length) {
      setRobloxProfiles({});
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API_URL}/roblox/profiles`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ user_ids: visibleRobloxIds }),
        });
        if (!response.ok || cancelled) return;
        const payload = await response.json();
        const next = {};
        for (const profile of payload.profiles ?? []) {
          if (profile?.user_id) next[String(profile.user_id)] = profile;
        }
        if (!cancelled) setRobloxProfiles((prev) => ({ ...prev, ...next }));
      } catch {
        if (!cancelled) setRobloxProfiles({});
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [visibleRobloxIds, token]);

  useEffect(() => {
    if (!token || !visibleDiscordIds.length) {
      setDiscordProfiles({});
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API_URL}/discord/profiles`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ user_ids: visibleDiscordIds }),
        });
        if (!response.ok || cancelled) return;
        const payload = await response.json();
        const next = {};
        for (const profile of payload.profiles ?? []) {
          if (profile?.user_id) next[String(profile.user_id)] = profile;
        }
        if (!cancelled) setDiscordProfiles((prev) => ({ ...prev, ...next }));
      } catch {
        if (!cancelled) setDiscordProfiles({});
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [visibleDiscordIds, token]);

  return (
    <>
      <section className="ws-panel">
        <PanelHeader icon="sports_esports" title="Roblox accounts" />
        <div className="ws-panel__body">
          {robloxAccounts.length ? (
            <>
              <div className="ws-account-grid">
                {robloxPage.slice.map((account) => {
                  const resolved = robloxProfiles[account.user_id] ?? {};
                  const displayName = account.username || resolved.username || `Account ${account.user_id}`;
                  const avatar = robloxHeadshotUrl({ ...account, headshot_url: resolved.headshot_url });
                  return (
                    <a
                      key={account.user_id}
                      href={`https://www.roblox.com/users/${encodeURIComponent(account.user_id)}/profile`}
                      target="_blank"
                      rel="noreferrer"
                      className="ws-account-card"
                    >
                      {avatar ? (
                        <img src={avatar} alt="" className="ws-account-card__avatar" loading="lazy" decoding="async" />
                      ) : (
                        <span className="ws-account-card__avatar" aria-hidden />
                      )}
                      <span className="ws-account-card__body">
                        <span className="ws-account-card__name">{displayName}</span>
                        <span className="ws-account-card__link">View profile</span>
                      </span>
                    </a>
                  );
                })}
              </div>
              <Pagination {...robloxPage} onPageChange={robloxPage.goTo} />
            </>
          ) : (
            <p className="muted">No Roblox accounts found on this device.</p>
          )}
        </div>
      </section>

      <section className="ws-panel">
        <PanelHeader icon="forum" title="Discord accounts" />
        <div className="ws-panel__body">
          {discordAccounts.length ? (
            <>
              <div className="ws-account-grid">
                {discordPage.slice.map((account) => {
                  const userId = String(account.user_id || "");
                  const resolved = discordProfiles[userId] ?? {};
                  const displayName =
                    resolved.display_name
                    || account.display_name
                    || `User ${userId}`;
                  const avatar =
                    resolved.avatar_url
                    || account.avatar_url
                    || discordAvatarUrl({
                      ...account,
                      avatar_hash: resolved.avatar_hash || account.avatar_hash,
                    });
                  const fallback = discordAvatarUrl({ user_id: userId });
                  return (
                    <div key={userId} className="ws-account-card ws-account-card--static">
                      {avatar ? (
                        <img
                          src={avatar}
                          alt=""
                          className="ws-account-card__avatar"
                          loading="lazy"
                          decoding="async"
                          onError={(event) => {
                            if (fallback && event.currentTarget.src !== fallback) {
                              event.currentTarget.src = fallback;
                            }
                          }}
                        />
                      ) : (
                        <span className="ws-account-card__avatar" aria-hidden />
                      )}
                      <span className="ws-account-card__body">
                        <span className="ws-account-card__name">{displayName}</span>
                        <span className="ws-account-card__link">Discord account</span>
                      </span>
                    </div>
                  );
                })}
              </div>
              <Pagination {...discordPage} onPageChange={discordPage.goTo} />
            </>
          ) : (
            <p className="muted">No Discord accounts found on this device.</p>
          )}
        </div>
      </section>
    </>
  );
}
