import React, { useState } from "react";
import { MaterialIcon } from "./MaterialIcon.jsx";

export function CollapseCard({
  icon = "folder",
  title,
  subtitle,
  badge = null,
  severity = "medium",
  defaultOpen = false,
  children,
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <article className={`ws-collapse-card ws-collapse-card--${severity} ${open ? "is-open" : ""}`}>
      <button type="button" className="ws-collapse-card__trigger" onClick={() => setOpen((v) => !v)}>
        <span className="ws-collapse-card__icon" aria-hidden>
          <MaterialIcon name={icon} size={18} />
        </span>
        <span className="ws-collapse-card__text">
          <strong>{title}</strong>
          {subtitle ? <span className="ws-collapse-card__sub">{subtitle}</span> : null}
        </span>
        {badge}
        <MaterialIcon name="expand_more" size={20} className="ws-collapse-card__chevron" />
      </button>
      {open ? <div className="ws-collapse-card__content">{children}</div> : null}
    </article>
  );
}
