import React from "react";

export function Pagination({ page, totalPages, total, pageSize, onPageChange }) {
  if (totalPages <= 1) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <nav className="ws-pagination" aria-label="Pagination">
      <button type="button" className="ws-pagination__btn" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        Previous
      </button>
      <span className="ws-pagination__meta">
        Page {page} of {totalPages}
        {total ? ` (${start}–${end} of ${total})` : null}
      </span>
      <button
        type="button"
        className="ws-pagination__btn"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
    </nav>
  );
}
