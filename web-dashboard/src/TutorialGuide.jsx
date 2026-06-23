import React from "react";
import { BookOpen, Keyboard, Search, X } from "lucide-react";
import { EXECUTOR_SEARCH_TERMS } from "./executorSearchTerms.js";
import { EXPERT_NAV_GROUPS, SIMPLE_TAB_GUIDE } from "./dashboardNav.js";

const TUTORIAL_SECTIONS = [
  {
    id: "quick-start",
    title: "Quick start (60 seconds)",
    steps: [
      "Open Summary and read the verdict and warning list.",
      "Open Last activity and check deletes and recent runs (newest at top).",
      "Press Ctrl+F (Windows) or Cmd+F (Mac) and search any program name from the catalog (e.g. Solara, Wave, Volt).",
      "If something looks deleted, open Advanced review and check the Deletions section.",
    ],
  },
  {
    id: "search",
    title: "How to search this report",
    body: [
      "Use the filter box at the top of Easy results to narrow the current tab.",
      "Use Ctrl+F / Cmd+F to search the entire page. Paths, program names, and timestamps are plain text.",
      "In Advanced review, each section has its own search box.",
      "Dates are MM/DD/YY HH:mm:ss (GMT+3). Search partial dates like 06/08/26.",
    ],
  },
  {
    id: "simple-tabs",
    title: "Easy results tabs",
    items: SIMPLE_TAB_GUIDE.map((tab) => ({
      title: `${tab.step}. ${tab.title}`,
      summary: tab.summary,
      hint: tab.searchHint,
    })),
  },
  {
    id: "expert",
    title: "Advanced review sections",
    groups: EXPERT_NAV_GROUPS.map((group) => ({
      title: group.label,
      description: group.description,
      sections: group.sectionIds,
    })),
  },
  {
    id: "deletions",
    title: "Deletes and cleanup timing",
    body: [
      "Delete-to-cleanup timing shows how long after a file was deleted the Recycle Bin was emptied.",
      "Evidence integrity flags when logs or traces look disabled, cleared, or recreated.",
      "If timeline data is thin, the report falls back to other logged signals on the PC.",
    ],
  },
  {
    id: "executors",
    title: "Program names to Ctrl+F",
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
              <h2 id="tutorial-title">{brandName} tutorial</h2>
              <p>How to read a scan. No account settings here.</p>
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
          <span className="tutorial-kbd-hint">
            <Search size={16} /> Use the filter box to narrow the active tab
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
                      <small>Search tip: {item.hint}</small>
                    </article>
                  ))}
                </div>
              ) : null}
              {section.groups ? (
                <div className="tutorial-card-grid">
                  {section.groups.map((group) => (
                    <article className="tutorial-card" key={group.title}>
                      <strong>{group.title}</strong>
                      <p>{group.description}</p>
                      <small>Sections: {group.sections.join(", ")}</small>
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
      <p className="muted">
        Try any program name, file paths, Recycle Bin, deleted, or dates like 06/08/26.
      </p>
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
