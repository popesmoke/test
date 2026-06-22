import React from "react";
import { Link } from "react-router-dom";

export function LegalDocument({ badge, title, highlight, updated, meta = [], children }) {
  return (
    <div className="legal-doc">
      <header className="legal-doc__hero">
        <span className="legal-doc__badge">{badge}</span>
        <h1>
          {title}
          {highlight ? <span className="legal-doc__highlight"> {highlight}</span> : null}
        </h1>
        <div className="legal-doc__meta">
          {updated ? <span>Updated {updated}</span> : null}
          {meta.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </header>
      <div className="legal-doc__body">{children}</div>
      <footer className="legal-doc__footer">
        <Link to="/">Home</Link>
        <Link to="/download">Download</Link>
        <Link to="/workspace">Review Console</Link>
        <a href="https://discord.gg/wPZXKaPyWY" target="_blank" rel="noreferrer">
          Discord
        </a>
      </footer>
    </div>
  );
}

export function LegalArticle({ index, title, children }) {
  return (
    <article className="legal-article" id={`article-${index}`}>
      <header className="legal-article__head">
        <span className="legal-article__index">{index}</span>
        <h2>{title}</h2>
      </header>
      <div className="legal-article__content">{children}</div>
    </article>
  );
}

/** @deprecated use LegalDocument */
export function LegalPage({ title, updated, children }) {
  return (
    <LegalDocument badge="Legal" title={title} updated={updated}>
      {children}
    </LegalDocument>
  );
}

/** @deprecated use LegalArticle */
export function LegalSection({ title, children }) {
  return (
    <section className="legal-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
