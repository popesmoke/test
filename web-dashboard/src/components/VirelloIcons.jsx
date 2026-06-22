import React from "react";

function IconBase({ children, size = 24, className = "" }) {
  return (
    <svg
      className={`v-icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function IconRadar({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" opacity="0.35" />
      <circle cx="12" cy="12" r="5.5" stroke="currentColor" strokeWidth="1.5" opacity="0.55" />
      <path d="M12 12 L20 8" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <path d="M7 16c1.2-1.4 2.7-2.2 5-2.2s3.8.8 5 2.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
    </IconBase>
  );
}

export function IconShieldMark({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <path
        d="M12 3.5 5 6.5v5.8c0 4.1 2.8 7.2 7 8.7 4.2-1.5 7-4.6 7-8.7V6.5L12 3.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M9.2 12.2 11 14l3.8-4.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </IconBase>
  );
}

export function IconTimer({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <circle cx="12" cy="13" r="7.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M12 9.5v4.2l2.6 1.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9.5 3.5h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M12 3.5v2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </IconBase>
  );
}

export function IconConsent({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <rect x="5" y="4" width="14" height="16" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M8.5 9.5h7M8.5 12.5h7M8.5 15.5h4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="16.5" cy="16.5" r="4.5" fill="var(--bg, #09090b)" stroke="currentColor" strokeWidth="1.5" />
      <path d="M15 16.5l1 1 2.2-2.2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </IconBase>
  );
}

export function IconConsole({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <rect x="3.5" y="5" width="17" height="12" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M7 9.5 9.5 12 7 14.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M11.5 14.5h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M3.5 9h17" stroke="currentColor" strokeWidth="1.2" opacity="0.4" />
    </IconBase>
  );
}

export function IconBolt({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <path
        d="M13.2 3 8 12.2h4.2L10.8 21l7.4-9.8H14L13.2 3Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </IconBase>
  );
}

export function IconDownload({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <path d="M12 4v9.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <path d="M8.5 11.5 12 15l3.5-3.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.5 18.5h13" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </IconBase>
  );
}

export function IconDiscord({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <path
        d="M18.9 6.2a14.5 14.5 0 0 0-3.6-1.2l-.2.4a13.4 13.4 0 0 0-5.8 0l-.2-.4a14.6 14.6 0 0 0-3.6 1.2C4.6 9.1 4 11.8 4.2 14.5a14.7 14.7 0 0 0 4.5 2.3l.9-1.4a9.7 9.7 0 0 1-1.5-.7l.3-.3c2.9 1.4 6 1.4 8.8 0l.3.3c-.5.3-1 .5-1.5.7l.9 1.4a14.6 14.6 0 0 0 4.5-2.3c.4-3.2-.3-5.9-2.1-8.3ZM9.7 12.8c-.8 0-1.5-.8-1.5-1.7s.7-1.7 1.5-1.7 1.5.8 1.5 1.7-.7 1.7-1.5 1.7Zm4.6 0c-.8 0-1.5-.8-1.5-1.7s.7-1.7 1.5-1.7 1.5.8 1.5 1.7-.7 1.7-1.5 1.7Z"
        fill="currentColor"
      />
    </IconBase>
  );
}

export function IconLock({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <rect x="6" y="10" width="12" height="9" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M8.5 10V8a3.5 3.5 0 0 1 7 0v2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="12" cy="14.5" r="1.2" fill="currentColor" />
    </IconBase>
  );
}

export function IconTarget({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <circle cx="12" cy="12" r="7.5" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="3.5" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
      <path d="M12 3v2M12 19v2M3 12h2M19 12h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </IconBase>
  );
}

export function IconUsers({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <circle cx="9" cy="9.5" r="2.8" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4.5 17.5c.8-2.4 2.4-3.7 4.5-3.7s3.7 1.3 4.5 3.7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="16.5" cy="10" r="2.2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M14 17.5c.4-1.6 1.4-2.5 2.8-2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </IconBase>
  );
}

export function IconWindows({ size, className }) {
  return (
    <IconBase size={size} className={className}>
      <path d="M4 5.5 11 4.2v7.3H4V5.5Zm0 8.3h7v7.3L4 19.3v-5.5Zm8.5-9.6L20 4.5v7.3h-7.5V4.2Zm0 8.3H20v7.8l-7.5-1.3v-6.5Z" fill="currentColor" />
    </IconBase>
  );
}
