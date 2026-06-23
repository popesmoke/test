import React from "react";
import { BookOpen, Keyboard, Search, X } from "lucide-react";
import { EXECUTOR_SEARCH_TERMS } from "./executorSearchTerms.js";
import { SIMPLE_TAB_GUIDE } from "./dashboardNav.js";

const TUTORIAL_SECTIONS = [
  {
    id: "quick-start",
    title: "Quick start",
    steps: [
      "Open Summary for the overall assessment and top concerns.",
      "Open Findings for the full list of warning signs and flagged programs.",
      "Open Activity for downloads and programs that ran on this PC.",
      "Open Accounts to see Roblox and Discord accounts found on the device.",
      "Use Ctrl+F (Windows) or Cmd+F (Mac) to search program names on the page.",
    ],
  },
  {
    id: "search",
    title: "How to search",
    body: [
      "Use Ctrl+F / Cmd+F to search the page for program names, file paths, or dates.",
      "Dates are shown as MM/DD/YY HH:mm:ss (GMT+3).",
      "File paths use %USERPROFILE% instead of the actual username.",
    ],
  },
  {
    id: "tabs",
    title: "Review sections",
    items: SIMPLE_TAB_GUIDE.map((tab) => ({
      title: `${tab.step}. ${tab.title}`,
      summary: tab.summary,
      hint: tab.searchHint,
    })),
  },
  {
    id: "deletions",
    title: "Deletions",
    body: [
      "When a file was deleted, the scan may still show a trace from system logs.",
      "If the Recycle Bin was emptied, the timing between delete and cleanup is shown.",
    ],
  },
  {
    id: "executors",
    title: "Program names to search",
    terms: EXECUTOR_SEARCH_TERMS,
  },
];

export function TutorialGuide({ open, onClose, brandName }) {
  if (!open) return null;

  return (
    <div className="tutorial-overlay" role="dialog" aria-modal="true" aria-labelledby="tutorial-title">
      <div className="tutorial-panel">
        <header className="tutorial-header">
          <div className="tutorial-header-title">
            <BookOpen size={22} />
            <div>
              <h2 id="tutorial-title">How to read a scan</h2>
              <p>A short guide to the review workspace.</p>
            </div>
          </div>
          <button type="button" className="tutorial-close" onClick={onClose} aria-label="Close tutorial">
            <X size={20} />
          </button>
        </header>

        <div className="tutorial-toolbar">
          <span className="tutorial-kbd-hint">
            <Keyboard size={16} /> Ctrl+F / Cmd+F searches this page
          </span>
        </div>

        <div className="tutorial-body">
          {TUTORIAL_SECTIONS.map((section) => (
            <section className="tutorial-section" key={section.id} id={`tutorial-${section.id}`}>
              <h3>{section.title}</h3>
              {section.steps ? (
                <ol className="tutorial-steps">
                  {section.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              ) : null}
              {section.body ? (
                <ul className="tutorial-bullets">
                  {section.body.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              ) : null}
              {section.items ? (
                <div className="tutorial-card-grid">
                  {section.items.map((item) => (
                    <article className="tutorial-card" key={item.title}>
                      <strong>{item.title}</strong>
                      <p>{item.summary}</p>
                      <small>{item.hint}</small>
                    </article>
                  ))}
                </div>
              ) : null}
              {section.terms ? (
                <div className="search-keyword-grid" aria-label="Program search keywords">
                  {section.terms.map((term) => (
                    <span className="search-keyword-chip" key={term}>
                      {term}
                    </span>
                  ))}
                </div>
              ) : null}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}

export function PageSearchIndex() {
  return (
    <aside className="page-search-index" aria-label="Searchable keywords for browser find">
      <p className="page-search-index-title">Search this page (Ctrl+F / Cmd+F)</p>
      <p className="muted">Try program names, file paths, or dates like 06/08/26.</p>
      <div className="search-keyword-grid">
        {EXECUTOR_SEARCH_TERMS.map((term) => (
          <span className="search-keyword-chip" key={`idx-${term}`}>
            {term}
          </span>
        ))}
      </div>
    </aside>
  );
}
