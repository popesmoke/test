import React from "react";

export function MaterialIcon({ name, size = 20, className = "", filled = false }) {
  return (
    <span
      className={`material-symbols-outlined${filled ? " material-symbols-filled" : ""} ${className}`.trim()}
      style={{ fontSize: size, lineHeight: 1 }}
      aria-hidden="true"
    >
      {name}
    </span>
  );
}

export function renderIcon(icon, size = 20, className = "") {
  if (!icon) return null;
  if (typeof icon === "string") {
    return <MaterialIcon name={icon} size={size} className={className} />;
  }
  const Icon = icon;
  return <Icon size={size} className={className} />;
}
