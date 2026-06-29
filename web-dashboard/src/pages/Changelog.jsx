import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchChangelog } from "../lib/siteApi.js";
import { LegalDocument } from "../components/LegalPage.jsx";

function formatDate(value) {
  if (!value) return "";
  return String(value).replace("T", " ").replace("Z", " UTC").slice(0, 16);
}

export function ChangelogPage() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void fetchChangelog()
      .then(setEntries)
      .finally(() => setLoading(false));
  }, []);

  return (
    <LegalDocument badge="Updates" title="Changelog" updated="Live feed">
      <p className="legal-doc__lead">
        Release notes and product updates for the Virello scanner and review console.
      </p>

      {loading ? <p className="muted">Loading changelog…</p> : null}

      {!loading && !entries.length ? (
        <div className="changelog-empty">
          <p>No published updates yet. Check back soon.</p>
          <Link to="/" className="btn btn--ghost">
            Back to home
          </Link>
        </div>
      ) : null}

      <div className="changelog-list">
        {entries.map((entry) => (
          <article key={entry.id} className="changelog-entry">
            <header className="changelog-entry__head">
              <span className="changelog-entry__version">v{entry.version}</span>
              <time className="changelog-entry__date">{formatDate(entry.published_at || entry.created_at)}</time>
            </header>
            <h2>{entry.title}</h2>
            <div className="changelog-entry__body">
              {String(entry.body || "")
                .split("\n")
                .filter(Boolean)
                .map((line) => (
                  <p key={line}>{line}</p>
                ))}
            </div>
          </article>
        ))}
      </div>
    </LegalDocument>
  );
}
