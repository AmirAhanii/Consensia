import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GradientBackground } from "../components/GradientBackground";
import { toast, ToastContainer } from "react-toastify";
import { API_BASE_URL } from "../config";

type ApiErrorResponse = {
  detail?: string;
  message?: string;
};

export default function RegisterPage() {
  const navigate = useNavigate();

  useEffect(() => {
    document.title = "Consensia — Register";
  }, []);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [institution, setInstitution] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();

    if (
      !fullName.trim() ||
      !email.trim() ||
      !password.trim() ||
      !confirmPassword.trim()
    ) {
      toast.error("Please fill in all required fields.");
      return;
    }

    if (password.length < 6) {
      toast.error("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    try {
      setIsSubmitting(true);

      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim(),
          password,
        }),
      });

      const data = (await response.json().catch(() => null)) as ApiErrorResponse | null;

      if (!response.ok) {
        throw new Error(
          data?.detail || data?.message || `Registration failed (${response.status})`
        );
      }

      toast.success("Registration successful. Please check your email to verify your account.");

      // Institution is currently not used by backend, but you can keep it locally if you want.
      if (institution.trim()) {
        localStorage.setItem("consensia_last_institution", institution.trim());
      }

      setTimeout(() => {
        navigate(`/verify-email?email=${encodeURIComponent(email.trim())}`);
      }, 1500);
    } catch (error) {
      console.error(error);
      toast.error(
        error instanceof Error
          ? error.message
          : "Something went wrong during registration."
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
                Join Consensia
              </p>

              <h1 className="mt-4 bg-gradient-to-br from-purple-100 via-purple-200 to-purple-400 bg-clip-text text-5xl font-bold tracking-tight text-transparent md:text-6xl">
                Create your account
              </h1>

              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-purple-200/85">
                Register to access the prototype workspace, create personas, run
                debates, and explore judge-generated consensus for
                software-engineering decision making.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-purple-300/15 bg-gradient-to-b from-purple-900/35 to-black/30 p-5">
                  <h3 className="text-lg font-semibold text-purple-100">
                    Multi-persona debates
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-purple-200/80">
                    Compare viewpoints from multiple software-engineering roles.
                  </p>
                </div>

                <div className="rounded-2xl border border-purple-300/15 bg-gradient-to-b from-purple-900/35 to-black/30 p-5">
                  <h3 className="text-lg font-semibold text-purple-100">
                    Judge synthesis
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-purple-200/80">
                    Review a final summary and reasoning generated from the
                    debate.
                  </p>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-purple-900/40 bg-black/60 p-6 shadow-xl shadow-purple-950/30 backdrop-blur">
              <h2 className="text-2xl font-semibold text-purple-100">
                Register
              </h2>
              <p className="mt-2 text-sm text-purple-300/70">
                Create an account to start using the prototype.
              </p>

              <form onSubmit={handleRegister} className="mt-6 space-y-4">
                <div>
                  <label className="mb-2 block text-sm text-purple-300">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Enter your full name"
                    className="w-full rounded-2xl border border-purple-900/50 bg-black/70 px-4 py-3 text-sm text-purple-100 outline-none transition focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40"
                  />
                </div>

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
                    Institution / Company
                  </label>
                  <input
                    type="text"
                    value={institution}
                    onChange={(e) => setInstitution(e.target.value)}
                    placeholder="Optional"
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
                    placeholder="Create a password"
                    className="w-full rounded-2xl border border-purple-900/50 bg-black/70 px-4 py-3 text-sm text-purple-100 outline-none transition focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm text-purple-300">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm your password"
                    className="w-full rounded-2xl border border-purple-900/50 bg-black/70 px-4 py-3 text-sm text-purple-100 outline-none transition focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full rounded-2xl bg-gradient-to-r from-purple-600 via-fuchsia-500 to-purple-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-purple-900/50 transition hover:shadow-fuchsia-500/40 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? "Creating account..." : "Sign Up"}
                </button>
              </form>

              <p className="mt-5 text-center text-sm text-purple-300/75">
                Already have an account?{" "}
                <Link
                  to="/login"
                  className="text-purple-100 underline underline-offset-4 hover:text-white"
                >
                  Log in
                </Link>
              </p>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}