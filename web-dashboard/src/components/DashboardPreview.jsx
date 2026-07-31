import React, { useCallback, useRef, useState } from "react";
import { MaterialIcon } from "./MaterialIcon.jsx";

const METRICS = [
  { label: "Total Scans", value: "12,543", trend: "+23.5%", icon: "radar", ok: false },
  { label: "Threats", value: "312", trend: "+12.7%", icon: "shield_alert", ok: false },
  { label: "Users", value: "5,682", trend: "+18.7%", icon: "users", ok: false },
  { label: "Clean", value: "11,231", trend: "+20.3%", icon: "check_circle", ok: true },
  { label: "Success", value: "99.3%", trend: "+1.6%", icon: "speed", ok: true },
];

const SCANS = [
  { user: "Player_1", result: "clean", threats: 0, time: "2m ago", type: "Screenshare" },
  { user: "xNova", result: "threat", threats: 3, time: "8m ago", type: "Scanner" },
  { user: "mod_kai", result: "clean", threats: 0, time: "14m ago", type: "Screenshare" },
  { user: "ash_rbx", result: "threat", threats: 1, time: "22m ago", type: "Scanner" },
  { user: "luna.exe", result: "clean", threats: 0, time: "31m ago", type: "Screenshare" },
];

const ALERTS = [
  { title: "High threat detected", detail: "Injector signature matched", time: "15m ago", tone: "bad", icon: "shield_alert" },
  { title: "Suspicious activity", detail: "Unusual process tree", time: "28m ago", tone: "warn", icon: "alert_triangle" },
  { title: "Mass scan detected", detail: "12 sessions in 5 min", time: "1h ago", tone: "bad", icon: "bolt" },
  { title: "New exploit signature", detail: "Watch list updated", time: "2h ago", tone: "info", icon: "fingerprint" },
];

const THREAT_BARS = [
  { name: "Synapse X", pct: 92 },
  { name: "Krnl", pct: 78 },
  { name: "Electron", pct: 64 },
  { name: "Fluxus", pct: 48 },
  { name: "Script-Ware", pct: 36 },
];

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "scans", label: "Scans", icon: "radar" },
  { id: "logs", label: "Logs", icon: "event_log" },
  { id: "users", label: "Users", icon: "users" },
  { id: "alerts", label: "Alerts", icon: "warning", badge: 12 },
  { id: "settings", label: "Settings", icon: "lock" },
];

export function DashboardPreview() {
  const cardRef = useRef(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [glow, setGlow] = useState({ x: 50, y: 40 });
  const [hovering, setHovering] = useState(false);

  const onMove = useCallback((event) => {
    const el = cardRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (event.clientX - rect.left) / rect.width;
    const py = (event.clientY - rect.top) / rect.height;
    setTilt({
      x: (py - 0.5) * -14,
      y: (px - 0.5) * 18,
    });
    setGlow({ x: px * 100, y: py * 100 });
  }, []);

  const onLeave = useCallback(() => {
    setHovering(false);
    setTilt({ x: 0, y: 0 });
    setGlow({ x: 50, y: 40 });
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
          className="dash-preview__card"
          style={{
            transform: `perspective(1200px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg) scale(${hovering ? 1.02 : 1})`,
            "--glow-x": `${glow.x}%`,
            "--glow-y": `${glow.y}%`,
          }}
        >
          <div className="dash-preview__shine" aria-hidden="true" />
          <aside className="dash-preview__nav">
            <div className="dash-preview__brand">
              <span className="dash-preview__brand-mark">
                <MaterialIcon name="radar" size={16} color="ffffff" />
              </span>
              <span>Virello</span>
            </div>
            <ul className="dash-preview__nav-list">
              {NAV.map((item) => (
                <li key={item.id} className={item.id === "dashboard" ? "is-active" : ""}>
                  <MaterialIcon name={item.icon} size={14} color={item.id === "dashboard" ? "ffffff" : "9aa3b2"} />
                  <span>{item.label}</span>
                  {item.badge ? <em>{item.badge}</em> : null}
                </li>
              ))}
            </ul>
            <div className="dash-preview__protect">
              <MaterialIcon name="shield" size={14} color="22c55e" />
              <div>
                <strong>Protection</strong>
                <span>Active</span>
              </div>
            </div>
          </aside>

          <div className="dash-preview__main">
            <header className="dash-preview__head">
              <div>
                <h3>Dashboard</h3>
                <p>Monitor scans and detect threats in real-time.</p>
              </div>
              <div className="dash-preview__head-actions">
                <span className="dash-preview__range">May 12 – May 18</span>
                <span className="dash-preview__cta">+ New Scan</span>
              </div>
            </header>

            <div className="dash-preview__metrics">
              {METRICS.map((m) => (
                <div key={m.label} className="dash-preview__metric">
                  <div className="dash-preview__metric-top">
                    <MaterialIcon name={m.icon} size={14} color={m.ok ? "22c55e" : "ef4444"} />
                    <span className={m.ok ? "is-ok" : ""}>{m.trend}</span>
                  </div>
                  <strong>{m.value}</strong>
                  <em>{m.label}</em>
                </div>
              ))}
            </div>

            <div className="dash-preview__grid">
              <div className="dash-preview__panel dash-preview__panel--scans">
                <div className="dash-preview__panel-head">
                  <h4>Recent Scans</h4>
                </div>
                <table>
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Result</th>
                      <th>Threats</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {SCANS.map((row) => (
                      <tr key={row.user}>
                        <td>
                          <span className="dash-preview__avatar">{row.user.slice(0, 1)}</span>
                          {row.user}
                        </td>
                        <td>
                          <span className={`dash-preview__pill dash-preview__pill--${row.result}`}>
                            {row.result === "clean" ? "Clean" : "Threat"}
                          </span>
                        </td>
                        <td>{row.threats}</td>
                        <td>{row.time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="dash-preview__side">
                <div className="dash-preview__panel">
                  <div className="dash-preview__panel-head">
                    <h4>Threats Over Time</h4>
                  </div>
                  <svg className="dash-preview__chart" viewBox="0 0 220 80" preserveAspectRatio="none" aria-hidden="true">
                    <defs>
                      <linearGradient id="threatFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ef4444" stopOpacity="0.35" />
                        <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <path
                      d="M0,58 C20,50 35,62 55,40 C75,18 95,28 115,22 C135,16 155,34 175,28 C195,22 210,12 220,18 L220,80 L0,80 Z"
                      fill="url(#threatFill)"
                    />
                    <path
                      d="M0,58 C20,50 35,62 55,40 C75,18 95,28 115,22 C135,16 155,34 175,28 C195,22 210,12 220,18"
                      fill="none"
                      stroke="#ef4444"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    />
                    <circle cx="115" cy="22" r="3.5" fill="#ef4444" />
                    <circle cx="175" cy="28" r="3.5" fill="#ef4444" />
                  </svg>
                </div>

                <div className="dash-preview__panel">
                  <div className="dash-preview__panel-head">
                    <h4>Top Threats</h4>
                  </div>
                  <ul className="dash-preview__bars">
                    {THREAT_BARS.map((bar) => (
                      <li key={bar.name}>
                        <span>{bar.name}</span>
                        <div>
                          <i style={{ width: `${bar.pct}%` }} />
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            <div className="dash-preview__bottom">
              <div className="dash-preview__panel">
                <div className="dash-preview__panel-head">
                  <h4>System Status</h4>
                </div>
                <ul className="dash-preview__status">
                  {["Real-time Scanning", "Screenshare Analysis", "Database", "API Service"].map((label) => (
                    <li key={label}>
                      <i />
                      <span>{label}</span>
                      <em>Active</em>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="dash-preview__panel">
                <div className="dash-preview__panel-head">
                  <h4>Recent Alerts</h4>
                </div>
                <ul className="dash-preview__alerts">
                  {ALERTS.map((alert) => (
                    <li key={alert.title} className={`tone-${alert.tone}`}>
                      <MaterialIcon name={alert.icon} size={14} color={alert.tone === "warn" ? "eab308" : alert.tone === "info" ? "a78bfa" : "ef4444"} />
                      <div>
                        <strong>{alert.title}</strong>
                        <span>{alert.detail}</span>
                      </div>
                      <em>{alert.time}</em>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="dash-preview__panel dash-preview__donut-wrap">
                <div className="dash-preview__panel-head">
                  <h4>Threats by Type</h4>
                </div>
                <div className="dash-preview__donut">
                  <svg viewBox="0 0 42 42" aria-hidden="true">
                    <circle cx="21" cy="21" r="15.5" fill="none" stroke="#1f2430" strokeWidth="5" />
                    <circle cx="21" cy="21" r="15.5" fill="none" stroke="#f97316" strokeWidth="5" strokeDasharray="45 55" strokeDashoffset="25" />
                    <circle cx="21" cy="21" r="15.5" fill="none" stroke="#3b82f6" strokeWidth="5" strokeDasharray="22 78" strokeDashoffset="-20" />
                    <circle cx="21" cy="21" r="15.5" fill="none" stroke="#ef4444" strokeWidth="5" strokeDasharray="15 85" strokeDashoffset="-42" />
                    <circle cx="21" cy="21" r="15.5" fill="none" stroke="#a855f7" strokeWidth="5" strokeDasharray="10 90" strokeDashoffset="-57" />
                  </svg>
                  <div className="dash-preview__donut-center">
                    <strong>312</strong>
                    <span>total</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <p className="dash-preview__hint">Hover to tilt the console preview</p>
    </div>
  );
}
