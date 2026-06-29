import React, { useEffect, useState } from "react";
import { fetchSiteAlerts } from "../lib/siteApi.js";

const DISMISS_KEY = "virello_dismissed_alerts";

function loadDismissed() {
  try {
    return new Set(JSON.parse(localStorage.getItem(DISMISS_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

export function SiteAlertBanner() {
  const [alerts, setAlerts] = useState([]);
  const [dismissed, setDismissed] = useState(loadDismissed);

  useEffect(() => {
    void fetchSiteAlerts().then(setAlerts).catch(() => setAlerts([]));
  }, []);

  const visible = alerts.filter((alert) => !dismissed.has(String(alert.id)));
  if (!visible.length) return null;

  function dismiss(id) {
    const next = new Set(dismissed);
    next.add(String(id));
    setDismissed(next);
    localStorage.setItem(DISMISS_KEY, JSON.stringify([...next]));
  }

  return (
    <div className="site-alerts">
      {visible.map((alert) => (
        <div key={alert.id} className={`site-alert site-alert--${alert.severity || "info"}`} role="status">
          <span>{alert.message}</span>
          {alert.dismissible ? (
            <button type="button" className="site-alert__dismiss" onClick={() => dismiss(alert.id)} aria-label="Dismiss">
              ×
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}
