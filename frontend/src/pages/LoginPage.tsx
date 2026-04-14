import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GradientBackground } from "../components/GradientBackground";
import { toast, ToastContainer } from "react-toastify";
import { API_BASE_URL } from "../config";
import "react-toastify/dist/ReactToastify.css";

type LoginResponse = {
  access_token: string;
  token_type: string;
};

type ApiErrorResponse = {
  detail?: string;
  message?: string;
};

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

      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const data = (await response.json().catch(() => null)) as
        | LoginResponse
        | ApiErrorResponse
        | null;

      if (!response.ok) {
        throw new Error(
          (data as ApiErrorResponse | null)?.detail ||
            (data as ApiErrorResponse | null)?.message ||
            `Login failed (${response.status})`
        );
      }

      const loginData = data as LoginResponse;

      localStorage.setItem("consensia_access_token", loginData.access_token);
      localStorage.setItem("consensia_token_type", loginData.token_type);
      localStorage.setItem("consensia_user_email", email.trim());

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
      <ToastContainer position="top-center" autoClose={4000} theme="dark" />

      <div className="relative z-10 min-h-screen bg-[#0d0618] px-6 py-10 text-purple-50">
        <div className="mx-auto max-w-6xl">
          <Link
            to="/"
            className="inline-flex items-center rounded-xl border border-purple-800/40 bg-black/40 px-4 py-2 text-sm text-purple-200 transition hover:border-purple-600 hover:text-white"
          >
            ← Back to Homepage
          </Link>

          <div className="mt-10 grid gap-10 lg:grid-cols-[1.05fr_0.95fr]">
            <section className="flex flex-col justify-center">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-fuchsia-300/80">
                Welcome back
              </p>

              <h1 className="mt-4 bg-gradient-to-br from-purple-100 via-purple-200 to-purple-400 bg-clip-text text-5xl font-bold tracking-tight text-transparent md:text-6xl">
                Log in to Consensia
              </h1>

              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-purple-200/85">
                Access your debate workspace, manage personas, and continue
                exploring multi-agent reasoning for software engineering.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-purple-300/15 bg-gradient-to-b from-purple-900/35 to-black/30 p-5">
                  <h3 className="text-lg font-semibold text-purple-100">
                    Continue your work
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-purple-200/80">
                    Return to the prototype and keep testing debate scenarios.
                  </p>
                </div>

                <div className="rounded-2xl border border-purple-300/15 bg-gradient-to-b from-purple-900/35 to-black/30 p-5">
                  <h3 className="text-lg font-semibold text-purple-100">
                    View AI consensus
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-purple-200/80">
                    Compare persona viewpoints with the final judge synthesis.
                  </p>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-purple-900/40 bg-black/60 p-6 shadow-xl shadow-purple-950/30 backdrop-blur">
              <h2 className="text-2xl font-semibold text-purple-100">
                Login
              </h2>
              <p className="mt-2 text-sm text-purple-300/70">
                Sign in to continue to the prototype.
              </p>

              <form onSubmit={handleLogin} className="mt-6 space-y-4">
                <div>
                  <label className="mb-2 block text-sm text-purple-300">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email"
                    className="w-full rounded-2xl border border-purple-900/50 bg-black/70 px-4 py-3 text-sm text-purple-100 outline-none transition focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm text-purple-300">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full rounded-2xl border border-purple-900/50 bg-black/70 px-4 py-3 text-sm text-purple-100 outline-none transition focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full rounded-2xl bg-gradient-to-r from-purple-600 via-fuchsia-500 to-purple-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-purple-900/50 transition hover:shadow-fuchsia-500/40 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? "Signing in..." : "Log In"}
                </button>
              </form>

              <p className="mt-5 text-center text-sm text-purple-300/75">
                Don’t have an account?{" "}
                <Link
                  to="/register"
                  className="text-purple-100 underline underline-offset-4"
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