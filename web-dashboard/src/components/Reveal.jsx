import React from "react";
import { useReveal } from "../hooks/useReveal.js";

export function Reveal({ children, className = "", delay = 0, as: Tag = "div" }) {
  const { ref, visible } = useReveal();

  return (
    <Tag
      ref={ref}
      className={`reveal${visible ? " reveal--visible" : ""}${className ? ` ${className}` : ""}`}
      style={{ "--reveal-delay": `${delay}ms` }}
    >
      {children}
    </Tag>
  );
}
