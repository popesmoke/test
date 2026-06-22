import React from "react";
import { Link } from "react-router-dom";

export function LegalPage({ title, updated, children }) {
  return (
    <article className="legal-page">
      <header className="legal-page__header">
        <p className="legal-page__eyebrow">Legal</p>
        <h1>{title}</h1>
        {updated ? <p className="legal-page__updated">Last updated: {updated}</p> : null}
      </header>
      <div className="legal-page__body">{children}</div>
      <footer className="legal-page__footer">
        <Link to="/">Back to home</Link>
        <span aria-hidden="true">·</span>
        <Link to="/workspace">Review Console</Link>
      </footer>
    </article>
  );
}

export function LegalSection({ title, children }) {
  return (
    <section className="legal-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
