import { useMemo, useState } from "react";

export function usePagination(items, pageSize = 8) {
  const [page, setPage] = useState(1);
  const total = items?.length ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const safePage = Math.min(Math.max(page, 1), totalPages);

  const slice = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return (items ?? []).slice(start, start + pageSize);
  }, [items, pageSize, safePage]);

  function goTo(nextPage) {
    setPage(Math.min(Math.max(nextPage, 1), totalPages));
  }

  function reset() {
    setPage(1);
  }

  return {
    page: safePage,
    totalPages,
    total,
    pageSize,
    slice,
    goTo,
    reset,
    hasPages: totalPages > 1,
  };
}
