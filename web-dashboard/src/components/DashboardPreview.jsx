import React, { useCallback, useRef, useState } from "react";
import { OverviewDashboard, DEMO_SESSIONS } from "../OverviewDashboard.jsx";

/**
 * Landing hero: the real console dashboard UI, scaled, with 3D tilt on hover.
 */
export function DashboardPreview() {
  const cardRef = useRef(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [glow, setGlow] = useState({ x: 50, y: 35 });
  const [hovering, setHovering] = useState(false);

  const onMove = useCallback((event) => {
    const el = cardRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (event.clientX - rect.left) / rect.width;
    const py = (event.clientY - rect.top) / rect.height;
    setTilt({
      x: (py - 0.5) * -10,
      y: (px - 0.5) * 14,
    });
    setGlow({ x: px * 100, y: py * 100 });
  }, []);

  const onLeave = useCallback(() => {
    setHovering(false);
    setTilt({ x: 0, y: 0 });
    setGlow({ x: 50, y: 35 });
  }, []);

  return (
    <div className="dash-preview">
      <div
        className={`dash-preview__stage${hovering ? " dash-preview__stage--live" : ""}`}
        onMouseEnter={() => setHovering(true)}
        onMouseMove={onMove}
        onMouseLeave={onLeave}
      >
        <div
          ref={cardRef}
          className="dash-preview__card dash-preview__card--live"
          style={{
            transform: `perspective(1400px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg) scale(${hovering ? 1.015 : 1})`,
            "--glow-x": `${glow.x}%`,
            "--glow-y": `${glow.y}%`,
          }}
        >
          <div className="dash-preview__shine" aria-hidden="true" />
          <div className="dash-preview__live" aria-hidden="true">
            <OverviewDashboard
              sessions={DEMO_SESSIONS}
              demo
              compact
              onOpenScan={() => {}}
              onNewScan={() => {}}
            />
          </div>
        </div>
      </div>
      <p className="dash-preview__hint">Hover to tilt — this is the real review console</p>
    </div>
  );
}
