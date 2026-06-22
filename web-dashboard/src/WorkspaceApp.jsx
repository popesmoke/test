import React from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Dashboard } from "./main.jsx";
import { getStoredToken, setStoredToken } from "./lib/auth.js";

export function WorkspaceApp() {
  const navigate = useNavigate();
  const token = getStoredToken();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  function logout() {
    setStoredToken("");
    navigate("/login", { replace: true });
  }

  return <Dashboard token={token} onLogout={logout} />;
}
