import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GradientBackground } from "../components/GradientBackground";
import { ThemedToastContainer } from "../components/ThemedToastContainer";
import { toast } from "react-toastify";
import {
  bodyMuted,
  eyebrowMuted,
  formCard,
  formHeading,
  formSub,
  ghostLinkBtn,
  heroTitleGradient,
  inputField,
  pageShell,
  primaryCta,
  promoCard,
} from "../theme/themeClasses";
import { API_BASE_URL } from "../config";
import { apiFetch, readResponseJson } from "../apiFetch";

type LoginResponse = {
  access_token: string;
  token_type: string;
};

type MeResponse = {
  full_name: string;
  is_admin?: boolean;
};

type ApiErrorResponse = {
  detail?: unknown;
  message?: string;
};

function formatApiDetail(detail: unknown): string {
  if (detail == null || detail === "") return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === "object" &&
        item !== null &&
        "msg" in item &&
        typeof (item as { msg: unknown }).msg === "string"
          ? (item as { msg: string }).msg
          : JSON.stringify(item)
      )
      .join(". ");
  }
  return String(detail);
}

export default function LoginPage() {
  const navigate = useNavigate();

  useEffect(() => {
    document.title = "Consensia — Login";
  }, []);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email.trim() || !password.trim()) {
      toast.error("Please enter your email and password.");
      return;
    }

    try {
      setIsSubmitting(true);

      const response = await apiFetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const data = (await readResponseJson<
        LoginResponse | ApiErrorResponse
      >(response).catch(() => null)) as LoginResponse | ApiErrorResponse | null;

      if (!response.ok) {
        const err = data as ApiErrorResponse | null;
        throw new Error(
          formatApiDetail(err?.detail) ||
            err?.message ||
            `Login failed (${response.status})`
        );
      }

      const loginData = data as LoginResponse;

      localStorage.setItem("consensia_access_token", loginData.access_token);
      localStorage.setItem("consensia_token_type", loginData.token_type);
      localStorage.setItem("consensia_user_email", email.trim());

      // Best-effort: load profile to show the user's name in chat UI.
      try {
        const meRes = await fetch(`${API_BASE_URL}/api/auth/me`, {
          headers: { Authorization: `Bearer ${loginData.access_token}` },
        });
        if (meRes.ok) {
          const me = (await readResponseJson<MeResponse>(meRes).catch(() => null)) as MeResponse | null;
          if (me?.full_name && me.full_name.trim()) {
            localStorage.setItem("consensia_user_name", me.full_name.trim());
          }
          if (me?.is_admin) {
            localStorage.setItem("consensia_is_admin", "1");
          } else {
            localStorage.removeItem("consensia_is_admin");
          }
        }
      } catch {
        // ignore
      }

      toast.success("Login successful.");
      navigate("/app");
    } catch (error) {
      console.error(error);
      toast.error(
        error instanceof Error ? error.message : "Something went wrong during login."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <GradientBackground />
      <ThemedToastContainer position="top-center" autoClose={4000} />

      <div className={`relative z-10 min-h-screen px-6 py-10 ${pageShell}`}>
        <div className="mx-auto max-w-6xl">
          <Link
            to="/"
            className={ghostLinkBtn}
          >
            ← Back to Homepage
          </Link>

          <div className="mt-10 grid gap-10 lg:grid-cols-[1.05fr_0.95fr]">
            <section className="flex flex-col justify-center">
              <p
                className={`text-sm font-semibold uppercase tracking-[0.2em] ${eyebrowMuted}`}
              >
                Welcome back
              </p>

              <h1
                className={`mt-4 bg-gradient-to-br bg-clip-text text-5xl font-bold tracking-tight text-transparent md:text-6xl ${heroTitleGradient}`}
              >
                Log in to Consensia
              </h1>

              <p className={`mt-6 max-w-2xl text-lg leading-relaxed ${bodyMuted}`}>
                Access your debate workspace, manage personas, and continue
                exploring multi-agent reasoning for software engineering.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <div className={promoCard}>
                  <h3 className="text-lg font-semibold text-purple-100 light:text-violet-900">
                    Continue your work
                  </h3>
                  <p className={`mt-2 text-sm leading-6 ${bodyMuted}`}>
                    Return to the prototype and keep testing debate scenarios.
                  </p>
                </div>

                <div className={promoCard}>
                  <h3 className="text-lg font-semibold text-purple-100 light:text-violet-900">
                    View AI consensus
                  </h3>
                  <p className={`mt-2 text-sm leading-6 ${bodyMuted}`}>
                    Compare persona viewpoints with the final judge synthesis.
                  </p>
                </div>
              </div>
            </section>

            <section className={formCard}>
              <h2 className={`text-2xl font-semibold ${formHeading}`}>Login</h2>
              <p className={`mt-2 text-sm ${formSub}`}>
                Sign in to continue to the prototype.
              </p>

              <form onSubmit={handleLogin} className="mt-6 space-y-4">
                <div>
                  <label className="mb-2 block text-sm text-purple-300 light:text-violet-700">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email"
                    className={`w-full px-4 py-3 text-sm ${inputField}`}
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm text-purple-300 light:text-violet-700">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className={`w-full px-4 py-3 text-sm ${inputField}`}
                  />
                  <div className="mt-2 text-right">
                    <Link
                      to="/forgot-password"
                      className="text-sm text-purple-200 underline underline-offset-4 light:text-violet-700"
                    >
                      Forgot password?
                    </Link>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={`w-full px-6 py-3 text-sm disabled:cursor-not-allowed ${primaryCta}`}
                >
                  {isSubmitting ? "Signing in..." : "Log In"}
                </button>
              </form>

              <p className={`mt-5 text-center text-sm text-purple-300/75 light:text-violet-600`}>
                Don’t have an account?{" "}
                <Link
                  to="/register"
                  className="text-purple-100 underline underline-offset-4 light:text-violet-800"
                >
                  Sign up
                </Link>
              </p>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}