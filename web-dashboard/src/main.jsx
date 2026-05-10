import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Clipboard, KeyRound, Lock, RefreshCw, ShieldCheck } from "lucide-react";
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

function JsonBlock({ value }) {
  return <pre className="terminal">{JSON.stringify(value ?? {}, null, 2)}</pre>;
}

function Results({ detail }) {
  const [tab, setTab] = useState("system_overview");
  const report = detail?.report ?? {};
  const tabs = [
    ["system_overview", "System Overview"],
    ["performance_environment", "Performance & Environment"],
    ["application_diagnostics", "Application Diagnostics"],
    ["security_integrity_signals", "Security / Integrity"],
    ["process_overview", "Processes"],
  ];

  if (!detail) {
    return <section className="empty-state">Select or generate a PIN session.</section>;
  }

  return (
    <section className="results">
      <div className="result-header">
        <div>
          <p className="eyebrow">Session PIN</p>
          <h2>{detail.pin}</h2>
        </div>
        <span className={`status large ${detail.status}`}>{detail.status}</span>
      </div>
      <div className="meta-grid">
        <span>Created: {new Date(detail.created_at).toLocaleString()}</span>
        <span>Expires: {new Date(detail.expires_at).toLocaleString()}</span>
        <span>Completed: {detail.completed_at ? new Date(detail.completed_at).toLocaleString() : "Waiting"}</span>
      </div>
      {detail.status !== "completed" ? (
        <div className="empty-state">Waiting for the desktop client to submit results.</div>
      ) : (
        <>
          <nav className="tabs">
            {tabs.map(([id, label]) => (
              <button className={tab === id ? "selected" : ""} onClick={() => setTab(id)} key={id}>
                {label}
              </button>
            ))}
          </nav>
          <JsonBlock value={report[tab]} />
        </>
      )}
    </section>
  );
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
