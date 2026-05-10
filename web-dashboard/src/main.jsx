import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ChevronUp,
  Clipboard,
  Cpu,
  Database,
  Download,
  FileText,
  Gamepad2,
  KeyRound,
  Lock,
  MemoryStick,
  RefreshCw,
  ScanSearch,
  Shield,
  ShieldCheck,
  Terminal,
  Trash2,
  Users,
} from "lucide-react";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "https://test-v7a8.onrender.com";

function authHeaders(token) {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

function Login({ onLogin }) {
  const [email, setEmail] = useState("checker@example.com");
  const [password, setPassword] = useState("change-me");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        setError("Login failed. Check the email and password.");
        return;
      }
      const data = await response.json();
      onLogin(data.token);
    } catch (error) {
      setError(`Could not reach backend at ${API_URL}`);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand-row">
          <ShieldCheck size={30} />
          <div>
            <h1>Checker Panel</h1>
            <p>Secure diagnostic review</p>
          </div>
        </div>
        <form onSubmit={submit} className="form-stack">
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="primary" type="submit">
            <Lock size={18} /> Sign in
          </button>
        </form>
      </section>
    </main>
  );
}

function SessionList({ sessions, selectedId, onSelect }) {
  return (
    <aside className="sidebar">
      <h2>PIN Sessions</h2>
      <div className="session-list">
        {sessions.map((session) => (
          <button
            className={`session-row ${selectedId === session.id ? "active" : ""}`}
            key={session.id}
            onClick={() => onSelect(session.id)}
          >
            <span className="pin">{session.pin}</span>
            <span className={`status ${session.status}`}>{session.status}</span>
            <small>{new Date(session.created_at).toLocaleString()}</small>
          </button>
        ))}
      </div>
    </aside>
  );
}

function TerminalBlock({ children }) {
  return <pre className="terminal">{children || "No relevant data found."}</pre>;
}

function asJson(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function lines(items, mapper) {
  if (!items || items.length === 0) return "";
  return items.map(mapper).filter(Boolean).join("\n");
}

function Card({ icon: Icon, title, children }) {
  return (
    <article className="result-card">
      <header className="card-title">
        <span className="icon-box"><Icon size={20} /></span>
        <h3>{title}</h3>
        <ChevronUp size={18} className="chevron" />
      </header>
      {children}
    </article>
  );
}

function RobloxSection({ report }) {
  const roblox = report.application_diagnostics?.roblox ?? {};
  const logs = roblox.logs ?? [];
  const accounts = [];
  for (const log of logs) {
    const signals = log.signals ?? {};
    for (const username of signals.usernames ?? []) {
      accounts.push({ label: username, detail: `Found in ${log.name}` });
    }
    for (const userId of signals.user_ids ?? []) {
      accounts.push({ label: `User ID ${userId}`, detail: `https://www.roblox.com/users/${userId}/profile` });
    }
  }

  return (
    <>
      <Card icon={Gamepad2} title="Roblox Accounts">
        <div className="account-list">
          {accounts.length === 0 ? (
            <p className="muted">No Roblox account identifiers found in approved logs.</p>
          ) : (
            accounts.slice(0, 40).map((account, index) => (
              <div className="account-row" key={`${account.label}-${index}`}>
                <div className="avatar">{account.label.slice(0, 1).toUpperCase()}</div>
                <div>
                  <strong>{account.label}</strong>
                  <span>{account.detail}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
      <Card icon={Users} title="Discord Accounts">
        <TerminalBlock>Discord account harvesting is not collected by this consent diagnostic build.</TerminalBlock>
      </Card>
      <Card icon={Gamepad2} title="Roblox Logs">
        <TerminalBlock>
          {lines(logs, (log) => {
            const signals = log.signals ?? {};
            return [
              `Log Name: ${log.name}`,
              `Date Modified: ${log.modified}`,
              `Usernames: ${(signals.usernames ?? []).join(", ") || "none"}`,
              `User IDs: ${(signals.user_ids ?? []).join(", ") || "none"}`,
              `Place IDs: ${(signals.place_ids ?? []).join(", ") || "none"}`,
              `LoadClientSettings: ${(signals.load_client_settings ?? []).length} line(s)`,
              "------------------------------------------------------------",
            ].join("\n");
          })}
        </TerminalBlock>
      </Card>
    </>
  );
}

function SystemSection({ report }) {
  const system = report.system_overview ?? {};
  const perf = report.performance_environment ?? {};
  const sec = report.security_integrity_signals ?? {};
  return (
    <>
      <Card icon={Cpu} title="Install Date">
        <TerminalBlock>
          {[
            `OS: ${system.os ?? "unknown"}`,
            `Hardware Model: ${system.hardware?.hardware_model ?? system.machine ?? "unknown"}`,
            `Architecture: ${system.machine ?? "unknown"}`,
            `CPU Cores: ${system.cpu_count_physical ?? "unknown"} physical / ${system.cpu_count_logical ?? "unknown"} logical`,
            `Boot Time: ${perf.boot_time ?? "unknown"}`,
            `Hashed Hostname: ${system.hostname_hash ?? "unknown"}`,
            `Hashed Hardware UUID: ${system.hardware?.uuid_hash ?? "unknown"}`,
          ].join("\n")}
        </TerminalBlock>
      </Card>
      <Card icon={Cpu} title="Services">
        <TerminalBlock>{sec.services?.raw}</TerminalBlock>
      </Card>
      <Card icon={Trash2} title="Recycle Bin">
        <TerminalBlock>{asJson(perf.trash)}</TerminalBlock>
      </Card>
      <Card icon={Terminal} title="Shell History">
        <TerminalBlock>{asJson(sec.command_history_keyword_hits)}</TerminalBlock>
      </Card>
    </>
  );
}

function BypassSection({ report }) {
  const sec = report.security_integrity_signals ?? {};
  return (
    <>
      <Card icon={Shield} title="Bypass Detection">
        <TerminalBlock>
          {[
            "Event Log / USN / Clearing Signals:",
            asJson(sec.deletion_and_log_clearing_signals),
            "",
            "Amcache Integrity:",
            asJson(sec.amcache),
            "",
            "Prefetch Health:",
            asJson(sec.prefetch_health),
            "",
            "Shellbag Signal:",
            asJson(sec.shellbag_clear_signal),
          ].join("\n")}
        </TerminalBlock>
      </Card>
      <Card icon={Shield} title="File Replacement">
        <TerminalBlock>{asJson(sec.roblox_executor_indicators?.traceback_or_log_hits)}</TerminalBlock>
      </Card>
    </>
  );
}

function RegistrySection({ report }) {
  const sec = report.security_integrity_signals ?? {};
  return (
    <>
      <Card icon={Database} title="Registry Activity">
        <TerminalBlock>
          {[
            "BAM Registry Entries:",
            asJson(sec.bam),
            "",
            "Shellbag Registry Signal:",
            asJson(sec.shellbag_clear_signal),
          ].join("\n")}
        </TerminalBlock>
      </Card>
      <Card icon={FileText} title="Execution Artifacts">
        <TerminalBlock>{asJson(report.performance_environment?.installed_applications)}</TerminalBlock>
      </Card>
    </>
  );
}

function FileAnalysisSection({ report }) {
  const sec = report.security_integrity_signals ?? {};
  return (
    <>
      <Card icon={ScanSearch} title="Execution Artifacts">
        <input className="section-search" placeholder="Search..." />
        <TerminalBlock>
          {[
            "Cheat Scan [Advanced]",
            "============================================================",
            asJson(sec.roblox_executor_indicators?.file_hits),
            "",
            "Prefetch Indicator Hits:",
            asJson(sec.prefetch_health?.indicator_hits),
          ].join("\n")}
        </TerminalBlock>
      </Card>
      <Card icon={ScanSearch} title="Unsigned / Missing Files">
        <TerminalBlock>Unsigned binary verification is not enabled in this prototype. Use indicator hits and Defender history for triage.</TerminalBlock>
      </Card>
    </>
  );
}

function SuspiciousFilesSection({ report }) {
  const sec = report.security_integrity_signals ?? {};
  return (
    <Card icon={ScanSearch} title="Suspicious Files">
      <TerminalBlock>
        {[
          "Recent files with matched indicator names:",
          asJson((sec.recent_items?.items ?? []).filter((item) => item.matched_indicator_names?.length)),
          "",
          "Defender Integrity:",
          asJson(sec.defender),
        ].join("\n")}
      </TerminalBlock>
    </Card>
  );
}

function CrashLogsSection({ report }) {
  const hits = report.security_integrity_signals?.roblox_executor_indicators?.traceback_or_log_hits ?? [];
  return (
    <Card icon={Terminal} title="Crash Logs">
      <TerminalBlock>{hits.length ? asJson(hits) : "No crash logs detected."}</TerminalBlock>
    </Card>
  );
}

function DeletionsSection({ report }) {
  const sec = report.security_integrity_signals ?? {};
  return (
    <Card icon={Trash2} title="File Deletions">
      <input className="section-search" placeholder="Search..." />
      <TerminalBlock>
        {[
          "Roblox Log Integrity Check:",
          asJson(report.application_diagnostics?.roblox),
          "",
          "Deleted / Clearing Signals:",
          asJson(sec.deletion_and_log_clearing_signals),
          "",
          "Recycle Bin:",
          asJson(report.performance_environment?.trash),
        ].join("\n")}
      </TerminalBlock>
    </Card>
  );
}

function MemorySection({ report }) {
  const processes = report.process_overview?.items ?? [];
  const robloxProcesses = processes.filter((proc) => (proc.name ?? "").toLowerCase().includes("roblox"));
  return (
    <>
      <Card icon={MemoryStick} title="Discord Downloads">
        <TerminalBlock>Discord download history is not collected by this consent diagnostic build.</TerminalBlock>
      </Card>
      <Card icon={MemoryStick} title="Roblox Memory Scan">
        <TerminalBlock>
          {robloxProcesses.length ? asJson(robloxProcesses) : "[OK] Roblox Memory: No running Roblox process found"}
        </TerminalBlock>
      </Card>
      <Card icon={MemoryStick} title="Injected Modules">
        <TerminalBlock>Injected module enumeration is not enabled in this prototype.</TerminalBlock>
      </Card>
    </>
  );
}

const resultSections = [
  { id: "roblox", label: "Roblox", icon: Gamepad2, component: RobloxSection },
  { id: "system", label: "System", icon: Cpu, component: SystemSection },
  { id: "bypass", label: "Bypass Detection", icon: Shield, component: BypassSection },
  { id: "registry", label: "Registry", icon: Database, component: RegistrySection },
  { id: "file-analysis", label: "File Analysis", icon: ScanSearch, component: FileAnalysisSection },
  { id: "custom", label: "Custom", icon: ScanSearch, component: FileAnalysisSection },
  { id: "suspicious", label: "Suspicious Files", icon: ScanSearch, component: SuspiciousFilesSection },
  { id: "crash", label: "Crash Logs", icon: Terminal, component: CrashLogsSection },
  { id: "deletions", label: "Deletions", icon: Trash2, component: DeletionsSection },
  { id: "memory", label: "Memory", icon: MemoryStick, component: MemorySection },
];

function Results({ detail }) {
  const [sectionId, setSectionId] = useState("roblox");
  const report = detail?.report ?? {};
  const activeSection = resultSections.find((section) => section.id === sectionId) ?? resultSections[0];
  const ActiveComponent = activeSection.component;

  if (!detail) {
    return <section className="empty-state">Select or generate a PIN session.</section>;
  }

  return (
    <section className="scan-results">
      <aside className="results-nav">
        <button className="back-link">← My Pins</button>
        <h2>Scan results</h2>
        <p>Submitted {detail.completed_at ? new Date(detail.completed_at).toLocaleString() : "Waiting"}</p>
        <button className="download-button" onClick={() => downloadReport(detail)}>
          <Download size={15} /> Download report
        </button>
        <nav>
          {resultSections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                className={sectionId === section.id ? "active" : ""}
                onClick={() => setSectionId(section.id)}
              >
                <Icon size={18} /> {section.label}
              </button>
            );
          })}
        </nav>
      </aside>
      <div className="result-content">
        <div className="result-header">
        <div>
          <p className="eyebrow">Session PIN</p>
          <h2>{detail.pin}</h2>
        </div>
        <span className={`status large ${detail.status}`}>{detail.status}</span>
        </div>
        {detail.status !== "completed" ? (
          <div className="empty-state">Waiting for the desktop client to submit results.</div>
        ) : (
          <ActiveComponent report={report} />
        )}
      </div>
    </section>
  );
}

function downloadReport(detail) {
  const blob = new Blob([JSON.stringify(detail, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `scan-${detail.pin}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function Dashboard({ token }) {
  const [sessions, setSessions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadSessions() {
    try {
      const response = await fetch(`${API_URL}/sessions`, { headers: authHeaders(token) });
      if (response.status === 401) {
        localStorage.removeItem("checkerToken");
        window.location.reload();
        return;
      }
      if (!response.ok) {
        throw new Error(`Session load failed: ${response.status}`);
      }
      const data = await response.json();
      setError("");
      setSessions(data);
      if (!selectedId && data[0]) {
        setSelectedId(data[0].id);
      }
    } catch (caught) {
      setError(`Could not load sessions from ${API_URL}. ${caught.message}`);
    }
  }

  async function createPin() {
    try {
      const response = await fetch(`${API_URL}/sessions`, { method: "POST", headers: authHeaders(token) });
      if (!response.ok) {
        throw new Error(`PIN creation failed: ${response.status}`);
      }
      const data = await response.json();
      setMessage(`Generated PIN ${data.pin}`);
      setSelectedId(data.id);
      await navigator.clipboard?.writeText(data.pin).catch(() => {});
      await loadSessions();
    } catch (caught) {
      setError(caught.message);
    }
  }

  useEffect(() => {
    loadSessions();
    const timer = setInterval(loadSessions, 5000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    fetch(`${API_URL}/sessions/${selectedId}`, { headers: authHeaders(token) })
      .then((response) => {
        if (!response.ok) throw new Error(`Result load failed: ${response.status}`);
        return response.json();
      })
      .then(setDetail)
      .catch((caught) => setError(caught.message));
  }, [selectedId, sessions]);

  const selectedPin = useMemo(() => sessions.find((session) => session.id === selectedId)?.pin, [sessions, selectedId]);

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <p className="eyebrow">Secure Remote System Diagnostic</p>
          <h1>Checker Dashboard</h1>
        </div>
        <div className="actions">
          {selectedPin && (
            <button onClick={() => navigator.clipboard?.writeText(selectedPin)}>
              <Clipboard size={18} /> Copy PIN
            </button>
          )}
          <button onClick={loadSessions}>
            <RefreshCw size={18} /> Refresh
          </button>
          <button className="primary" onClick={createPin}>
            <KeyRound size={18} /> Generate New PIN
          </button>
        </div>
      </header>
      {message && <div className="notice">{message}</div>}
      {error && <div className="error-banner">{error}</div>}
      <div className="layout">
        <SessionList sessions={sessions} selectedId={selectedId} onSelect={setSelectedId} />
        <Results detail={detail} />
      </div>
    </main>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("checkerToken") ?? "");
  function login(nextToken) {
    localStorage.setItem("checkerToken", nextToken);
    setToken(nextToken);
  }
  return token ? <Dashboard token={token} /> : <Login onLogin={login} />;
}

try {
  createRoot(document.getElementById("root")).render(<App />);
} catch (error) {
  document.body.innerHTML = `<main class="login-shell"><section class="login-panel"><h1>Dashboard Error</h1><p class="error">${error.message}</p></section></main>`;
}
