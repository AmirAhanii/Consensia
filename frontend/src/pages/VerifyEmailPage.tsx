import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { GradientBackground } from "../components/GradientBackground";
import { API_BASE_URL } from "../config";
import { toast, ToastContainer } from "react-toastify";

type VerifyState = "idle" | "loading" | "success" | "error";

type ApiErrorResponse = {
  detail?: string;
  message?: string;
};

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const email = useMemo(
    () => searchParams.get("email")?.trim() || "",
    [searchParams],
  );

  const [status, setStatus] = useState<VerifyState>("idle");
  const [message, setMessage] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);

  useEffect(() => {
    document.title = "Consensia — Verify Email";
  }, []);

  useEffect(() => {
    if (!email) {
      setStatus("error");
      setMessage("Missing email address.");
      return;
    }

    setStatus("idle");
    setMessage("Enter the 6-digit code we sent to your email.");
  }, [email]);

  useEffect(() => {
    if (status !== "success") return;

    const timer = window.setTimeout(() => {
      navigate("/login");
    }, 1500);

    return () => window.clearTimeout(timer);
  }, [status, navigate]);

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      setStatus("error");
      setMessage("Missing email address.");
      return;
    }

    const code = verificationCode.trim();

    if (!/^\d{6}$/.test(code)) {
      setStatus("error");
      setMessage("Please enter a valid 6-digit verification code.");
      return;
    }

    try {
      setIsSubmitting(true);
      setStatus("loading");
      setMessage("Verifying your code...");

      const response = await fetch(`${API_BASE_URL}/api/auth/verify-email`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          code,
        }),
      });

      const data = (await response.json().catch(() => null)) as ApiErrorResponse | null;

      if (!response.ok) {
        throw new Error(
          data?.detail || data?.message || `Verification failed (${response.status})`,
        );
      }

      setStatus("success");
      setMessage("Your email has been verified successfully. Redirecting to login...");
      toast.success("Email verified successfully.");
    } catch (error) {
      console.error(error);
      setStatus("error");
      setMessage(
        error instanceof Error
          ? error.message
          : "Something went wrong while verifying your email.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendVerification = async () => {
    if (!email) {
      toast.error("Missing email address.");
      return;
    }

    try {
      setIsResending(true);

      const response = await fetch(`${API_BASE_URL}/api/auth/resend-verification`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      });

      const data = (await response.json().catch(() => null)) as ApiErrorResponse | null;

      if (!response.ok) {
        throw new Error(
          data?.detail || data?.message || `Resend failed (${response.status})`,
        );
      }

      toast.success(data?.message || "A new verification code has been sent.");
      setStatus("idle");
      setMessage("We sent a new 6-digit verification code to your email.");
    } catch (error) {
      console.error(error);
      toast.error(
        error instanceof Error
          ? error.message
          : "Something went wrong while resending the verification code.",
      );
    } finally {
      setIsResending(false);
    }
  };

  const cardBorder =
    status === "success"
      ? "border-emerald-500/30"
      : status === "error"
        ? "border-red-500/30"
        : "border-purple-900/40";

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
                Email Verification
              </p>

              <h1 className="mt-4 bg-gradient-to-br from-purple-100 via-purple-200 to-purple-400 bg-clip-text text-5xl font-bold tracking-tight text-transparent md:text-6xl">
                Confirm your account
              </h1>

              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-purple-200/85">
                Enter the verification code sent to your email to activate your
                Consensia account and continue to login.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-purple-300/15 bg-gradient-to-b from-purple-900/35 to-black/30 p-5">
                  <h3 className="text-lg font-semibold text-purple-100">
                    Secure onboarding
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-purple-200/80">
                    Email verification helps confirm account ownership before
                    access.
                  </p>
                </div>

                <div className="rounded-2xl border border-purple-300/15 bg-gradient-to-b from-purple-900/35 to-black/30 p-5">
                  <h3 className="text-lg font-semibold text-purple-100">
                    Ready for login
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-purple-200/80">
                    Once verified, you will be redirected to the login page.
                  </p>
                </div>
              </div>
            </section>

            <section
              className={`rounded-3xl ${cardBorder} bg-black/60 p-6 shadow-xl shadow-purple-950/30 backdrop-blur`}
            >
              <h2 className="text-2xl font-semibold text-purple-100">
                Verify Email
              </h2>

              <p className="mt-2 text-sm text-purple-300/70">
                Account:{" "}
                <span className="text-purple-100">
                  {email || "Unknown email"}
                </span>
              </p>

              <div className="mt-8 rounded-2xl border border-purple-300/10 bg-purple-950/20 p-5">
                <form onSubmit={handleVerifyCode} className="space-y-4">
                  <div>
                    <label className="mb-2 block text-sm text-purple-300">
                      6-digit verification code
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      maxLength={6}
                      value={verificationCode}
                      onChange={(e) =>
                        setVerificationCode(e.target.value.replace(/\D/g, ""))
                      }
                      placeholder="Enter code"
                      className="w-full rounded-2xl border border-purple-900/50 bg-black/70 px-4 py-3 text-sm tracking-[0.3em] text-purple-100 outline-none transition focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40"
                    />
                  </div>

                  {status === "loading" && (
                    <div className="flex items-center gap-3">
                      <div className="h-5 w-5 animate-spin rounded-full border-2 border-purple-300/30 border-t-fuchsia-400" />
                      <p className="text-sm text-purple-200">{message}</p>
                    </div>
                  )}

                  {status !== "loading" && message && (
                    <p
                      className={`text-sm font-medium ${
                        status === "success"
                          ? "text-emerald-300"
                          : status === "error"
                            ? "text-red-300"
                            : "text-purple-200"
                      }`}
                    >
                      {message}
                    </p>
                  )}

                  <div className="flex flex-wrap gap-3">
                    <button
                      type="submit"
                      disabled={isSubmitting || !email}
                      className="inline-flex items-center rounded-xl bg-gradient-to-r from-purple-600 via-fuchsia-500 to-purple-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-purple-900/50 transition hover:shadow-fuchsia-500/40 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isSubmitting ? "Verifying..." : "Verify code"}
                    </button>

                    <button
                      type="button"
                      onClick={handleResendVerification}
                      disabled={isResending || !email}
                      className="inline-flex items-center rounded-xl border border-purple-800/40 bg-black/40 px-5 py-3 text-sm text-purple-200 transition hover:border-purple-600 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isResending ? "Sending..." : "Resend code"}
                    </button>

                    <Link
                      to="/register"
                      className="inline-flex items-center rounded-xl border border-purple-800/40 bg-black/40 px-5 py-3 text-sm text-purple-200 transition hover:border-purple-600 hover:text-white"
                    >
                      Back to Register
                    </Link>
                  </div>
                </form>
              </div>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}