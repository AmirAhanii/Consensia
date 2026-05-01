import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { GradientBackground } from "../components/GradientBackground";
import { ThemedToastContainer } from "../components/ThemedToastContainer";
import { toast } from "react-toastify";
import { authApiFetch, readResponseJson } from "../apiFetch";
import { clearAuthSession, getAccessToken } from "../authHeaders";
import {
  appearanceSegmentTrack,
  bodyMuted,
  dangerGhostBtn,
  eyebrowMuted,
  formCard,
  formHeading,
  formSub,
  ghostLinkBtn,
  heroTitleGradient,
  inputField,
  pageShell,
  primaryCta,
  profileMutedCard,
} from "../theme/themeClasses";
import { useTheme } from "../theme/ThemeContext";

type MeResponse = {
  id: string;
  email: string;
  full_name: string;
  is_email_verified: boolean;
  auth_provider: string;
  is_admin?: boolean;
};

type ApiErrorResponse = {
  detail?: string;
  message?: string;
};

export default function ProfilePage() {
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    document.title = "Consensia — Profile";
  }, []);

  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState<MeResponse | null>(null);

  const [fullName, setFullName] = useState("");
  const [savingName, setSavingName] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  const [deletePassword, setDeletePassword] = useState("");
  const [deleting, setDeleting] = useState(false);

  const loadMe = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    try {
      setLoading(true);
      const res = await authApiFetch("/api/auth/me");
      const data = (await readResponseJson<MeResponse | ApiErrorResponse>(
        res
      ).catch(() => null)) as MeResponse | ApiErrorResponse | null;
      if (res.status === 401) {
        clearAuthSession();
        toast.error("Session expired. Please sign in again.");
        navigate("/login", { replace: true });
        return;
      }
      if (!res.ok) {
        throw new Error(
          (data as ApiErrorResponse | null)?.detail ||
            (data as ApiErrorResponse | null)?.message ||
            `Could not load profile (${res.status})`
        );
      }
      const profile = data as MeResponse;
      setMe(profile);
      setFullName(profile.full_name);
      if (profile.full_name?.trim()) {
        localStorage.setItem("consensia_user_name", profile.full_name.trim());
      }
    } catch (e) {
      console.error(e);
      toast.error(e instanceof Error ? e.message : "Could not load profile.");
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    void loadMe();
  }, [loadMe]);

  const isLocal = me?.auth_provider === "local";

  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = fullName.trim();
    if (!trimmed) {
      toast.error("Display name cannot be empty.");
      return;
    }
    try {
      setSavingName(true);
      const res = await authApiFetch("/api/auth/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: trimmed }),
      });
      const data = (await readResponseJson<MeResponse | ApiErrorResponse>(
        res
      ).catch(() => null)) as MeResponse | ApiErrorResponse | null;
      if (!res.ok) {
        throw new Error(
          (data as ApiErrorResponse | null)?.detail ||
            (data as ApiErrorResponse | null)?.message ||
            `Update failed (${res.status})`
        );
      }
      const updated = data as MeResponse;
      setMe(updated);
      setFullName(updated.full_name);
      if (updated.full_name?.trim()) {
        localStorage.setItem("consensia_user_name", updated.full_name.trim());
      }
      toast.success("Display name updated.");
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Could not update name.");
    } finally {
      setSavingName(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 6) {
      toast.error("New password must be at least 6 characters.");
      return;
    }
    try {
      setChangingPassword(true);
      const res = await authApiFetch("/api/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      const data = (await readResponseJson<{ message?: string } | ApiErrorResponse>(
        res
      ).catch(() => null)) as { message?: string } | ApiErrorResponse | null;
      if (!res.ok) {
        throw new Error(
          (data as ApiErrorResponse | null)?.detail ||
            (data as ApiErrorResponse | null)?.message ||
            `Could not change password (${res.status})`
        );
      }
      setCurrentPassword("");
      setNewPassword("");
      toast.success("Password updated.");
    } catch (err) {
      console.error(err);
      toast.error(
        err instanceof Error ? err.message : "Could not change password."
      );
    } finally {
      setChangingPassword(false);
    }
  };

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !window.confirm(
        "Delete your account permanently? This cannot be undone. All saved debates will be removed."
      )
    ) {
      return;
    }
    try {
      setDeleting(true);
      const res = await authApiFetch("/api/auth/delete-account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: deletePassword }),
      });
      const data = (await readResponseJson<{ message?: string } | ApiErrorResponse>(
        res
      ).catch(() => null)) as { message?: string } | ApiErrorResponse | null;
      if (!res.ok) {
        throw new Error(
          (data as ApiErrorResponse | null)?.detail ||
            (data as ApiErrorResponse | null)?.message ||
            `Could not delete account (${res.status})`
        );
      }
      clearAuthSession();
      toast.success("Account deleted.");
      navigate("/login", { replace: true });
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Could not delete account.");
    } finally {
      setDeleting(false);
    }
  };

  const handleLogout = () => {
    clearAuthSession();
    navigate("/login", { replace: true });
  };

  return (
    <>
      <GradientBackground />
      <ThemedToastContainer position="top-center" autoClose={4000} />

      <div className={`relative z-10 min-h-screen px-6 py-10 ${pageShell}`}>
        <div className="mx-auto max-w-3xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Link
              to="/app"
              className={ghostLinkBtn}
            >
              ← Back to workspace
            </Link>
            <button
              type="button"
              onClick={handleLogout}
              className={`rounded-xl px-4 py-2 text-sm ${dangerGhostBtn}`}
            >
              Log out
            </button>
          </div>

          <header className="mt-10">
            <p
              className={`text-sm font-semibold uppercase tracking-[0.2em] ${eyebrowMuted}`}
            >
              Your account
            </p>
            <h1
              className={`mt-3 bg-gradient-to-br bg-clip-text text-4xl font-bold tracking-tight text-transparent md:text-5xl ${heroTitleGradient}`}
            >
              Profile & settings
            </h1>
            <p className={`mt-4 max-w-2xl ${bodyMuted}`}>
              Update how you appear in Consensia, change your password, or delete your
              account. Password actions require your current password, like signing in.
            </p>
          </header>

          {loading ? (
            <p className="mt-12 text-center text-purple-400 light:text-violet-600">
              Loading…
            </p>
          ) : me ? (
            <div className="mt-10 space-y-8">
              <section className={formCard}>
                <h2 className={`text-lg font-semibold ${formHeading}`}>Account</h2>
                <p className={`mt-1 text-sm ${formSub}`}>
                  Signed in as{" "}
                  <span className="text-purple-100 light:text-violet-900">{me.email}</span>
                </p>
                {!me.is_email_verified ? (
                  <p className="mt-2 text-sm text-amber-300/90 light:text-amber-800/90">
                    Email not verified — check your inbox or use the verify link from
                    registration.
                  </p>
                ) : null}
                {me.is_admin ? (
                  <p className="mt-2 text-sm text-emerald-300/90 light:text-emerald-800/90">
                    Team admin — unlimited daily debates on this workspace.
                  </p>
                ) : null}
              </section>

              <section className={formCard}>
                <h2 className={`text-lg font-semibold ${formHeading}`}>Display name</h2>
                <p className={`mt-1 text-sm ${formSub}`}>
                  Shown in the app where your name appears.
                </p>
                <form onSubmit={handleSaveName} className="mt-5 space-y-4">
                  <div>
                    <label className={`mb-2 block text-sm ${formSub}`}>Name</label>
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className={inputField}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={savingName}
                    className={`rounded-2xl px-6 py-2.5 text-sm font-semibold ${primaryCta}`}
                  >
                    {savingName ? "Saving…" : "Save name"}
                  </button>
                </form>
              </section>

              {isLocal ? (
                <section className={formCard}>
                  <h2 className={`text-lg font-semibold ${formHeading}`}>
                    Change password
                  </h2>
                  <p className={`mt-1 text-sm ${formSub}`}>
                    Enter your current password, then choose a new one (at least 6
                    characters).
                  </p>
                  <form onSubmit={handleChangePassword} className="mt-5 space-y-4">
                    <div>
                      <label className={`mb-2 block text-sm ${formSub}`}>
                        Current password
                      </label>
                      <input
                        type="password"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        autoComplete="current-password"
                        className={inputField}
                      />
                    </div>
                    <div>
                      <label className={`mb-2 block text-sm ${formSub}`}>
                        New password
                      </label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        autoComplete="new-password"
                        className={inputField}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={changingPassword}
                      className={`rounded-2xl px-6 py-2.5 text-sm font-semibold ${primaryCta}`}
                    >
                      {changingPassword ? "Updating…" : "Update password"}
                    </button>
                  </form>
                </section>
              ) : (
                <section
                  className={profileMutedCard}
                >
                  <h2 className={`text-lg font-semibold ${formHeading}`}>Password</h2>
                  <p className={`mt-2 text-sm ${formSub}`}>
                    You signed in with Google. Password change and password-based account
                    deletion are only available for email/password accounts.
                  </p>
                </section>
              )}

              {isLocal ? (
                <section className="rounded-3xl border border-rose-900/35 bg-[var(--c-surface-rose-section)] p-6 shadow-xl shadow-black/20 backdrop-blur light:border-rose-300/60 light:shadow-[color:var(--c-shadow-card)]">
                  <h2 className="text-lg font-semibold text-rose-200 light:text-rose-800">
                    Delete account
                  </h2>
                  <p className={`mt-1 text-sm ${formSub}`}>
                    Permanently remove your account and all saved debates. Enter your
                    password to confirm.
                  </p>
                  <form onSubmit={handleDeleteAccount} className="mt-5 space-y-4">
                    <div>
                      <label className={`mb-2 block text-sm ${formSub}`}>
                        Password
                      </label>
                      <input
                        type="password"
                        value={deletePassword}
                        onChange={(e) => setDeletePassword(e.target.value)}
                        autoComplete="current-password"
                        className="w-full rounded-2xl border border-rose-900/40 bg-[var(--c-surface-rose-field)] px-4 py-3 text-sm text-[var(--c-fg)] outline-none transition focus:border-rose-500 focus:ring-2 focus:ring-rose-500/30 light:border-rose-400/55 light:focus:border-rose-500"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={deleting}
                      className="rounded-2xl border border-rose-600/60 bg-rose-950/40 px-6 py-2.5 text-sm font-semibold text-rose-100 transition hover:bg-rose-900/50 disabled:cursor-not-allowed disabled:opacity-60 light:border-rose-400 light:bg-rose-100 light:text-rose-900 light:hover:bg-rose-200/80"
                    >
                      {deleting ? "Deleting…" : "Delete my account"}
                    </button>
                  </form>
                </section>
              ) : null}

              <section className={formCard}>
                <h2 className={`text-lg font-semibold ${formHeading}`}>Appearance</h2>
                <p className={`mt-1 text-sm ${formSub}`}>
                  Optional: switch between dark workspace and light, whitish-purple theme.
                </p>
                <div className={`mt-4 ${appearanceSegmentTrack}`}>
                  <button
                    type="button"
                    onClick={() => setTheme("dark")}
                    className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium transition ${
                      theme === "dark"
                        ? "bg-purple-900/70 text-white shadow-sm light:bg-violet-700 light:text-white"
                        : "text-purple-400 hover:text-purple-200 light:text-violet-600 light:hover:text-violet-900"
                    }`}
                  >
                    <Moon className="h-4 w-4 shrink-0 opacity-90" aria-hidden />
                    Dark
                  </button>
                  <button
                    type="button"
                    onClick={() => setTheme("light")}
                    className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium transition ${
                      theme === "light"
                        ? "bg-purple-900/70 text-white shadow-sm light:bg-violet-600 light:text-white"
                        : "text-purple-400 hover:text-purple-200 light:text-violet-600 light:hover:text-violet-900"
                    }`}
                  >
                    <Sun className="h-4 w-4 shrink-0 opacity-90" aria-hidden />
                    Light
                  </button>
                </div>
              </section>
            </div>
          ) : (
            <p className="mt-12 text-center text-purple-400 light:text-violet-600">
              Could not load profile.
            </p>
          )}
        </div>
      </div>
    </>
  );
}
