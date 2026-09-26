import React from "react";
import { OverviewDashboard, DEMO_SESSIONS } from "../OverviewDashboard.jsx";

/** Landing hero: static product frame of the real review console (no tilt/glow). */
export function DashboardPreview() {
  return (
    <div className="dash-preview">
      <div className="dash-preview__stage">
        <div className="dash-preview__card dash-preview__card--live">
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
      <p className="dash-preview__hint">Review console preview</p>
    </div>
  );
}
