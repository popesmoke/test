import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { SiteLayout } from "./components/SiteLayout.jsx";
import { AboutPage } from "./pages/About.jsx";
import { DownloadPage } from "./pages/Download.jsx";
import { LandingPage } from "./pages/Landing.jsx";
import { LoginPage } from "./pages/Login.jsx";
import { PrivacyPolicyPage } from "./pages/PrivacyPolicy.jsx";
import { PurchasePage } from "./pages/Purchase.jsx";
import { TermsOfServicePage } from "./pages/TermsOfService.jsx";
import { WorkspaceApp } from "./WorkspaceApp.jsx";

export function AppRouter({ loginError }) {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<SiteLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="download" element={<DownloadPage />} />
          <Route path="purchase" element={<PurchasePage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="privacy" element={<PrivacyPolicyPage />} />
          <Route path="tos" element={<TermsOfServicePage />} />
          <Route path="terms" element={<Navigate to="/tos" replace />} />
        </Route>
        <Route path="login" element={<LoginPage loginError={loginError} />} />
        <Route path="workspace/*" element={<WorkspaceApp />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
