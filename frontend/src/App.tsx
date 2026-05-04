import React from "react";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import DebatePage from "./pages/DebatePage";
import RegisterPage from "./pages/RegisterPage";
import LoginPage from "./pages/LoginPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ProfilePage from "./pages/ProfilePage";
import AdminStatsPage from "./pages/AdminStatsPage";

/** When the SPA loads on `/…/assets/…` (e.g. PDF in new tab), show the file in an iframe instead of redirecting home. */
function AssetsDocumentShell() {
  const src = window.location.href;
  return (
    <div className="flex min-h-screen flex-col bg-[#0b0614] text-purple-100 light:bg-violet-50 light:text-violet-950">
      <header className="border-b border-purple-500/20 px-4 py-3 light:border-violet-200">
        <Link to="/" className="text-sm font-medium text-fuchsia-300 hover:underline light:text-fuchsia-800">
          ← Back to home
        </Link>
      </header>
      <iframe title="Document" src={src} className="min-h-0 w-full flex-1 border-0 bg-neutral-950 light:bg-white" />
    </div>
  );
}

function CatchAll() {
  if (window.location.pathname.includes("/assets/")) {
    return <AssetsDocumentShell />;
  }
  return <Navigate to="/" replace />;
}

function App() {
  const basename =
    import.meta.env.BASE_URL.replace(/\/$/, "") || undefined;

  return (
    <BrowserRouter basename={basename}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/app" element={<DebatePage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/admin" element={<AdminStatsPage />} />
        <Route path="*" element={<CatchAll />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;