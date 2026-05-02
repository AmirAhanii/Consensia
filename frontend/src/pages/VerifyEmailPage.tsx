import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { GradientBackground } from "../components/GradientBackground";
import { ThemedToastContainer } from "../components/ThemedToastContainer";
import { API_BASE_URL } from "../config";
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
                Email Verification
              </p>

              <h1
                className={`mt-4 bg-gradient-to-br bg-clip-text text-5xl font-bold tracking-tight text-transparent md:text-6xl ${heroTitleGradient}`}
              >
                Confirm your account
              </h1>

              <p className={`mt-6 max-w-2xl text-lg leading-relaxed ${bodyMuted}`}>
                Enter the verification code sent to your email to activate your
                Consensia account and continue to login.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <div className={promoCard}>
                  <h3 className="text-lg font-semibold text-purple-100 light:text-violet-900">
                    Secure onboarding
                  </h3>
                  <p className={`mt-2 text-sm leading-6 ${bodyMuted}`}>
                    Email verification helps confirm account ownership before
                    access.
                  </p>
                </div>

                <div className={promoCard}>
                  <h3 className="text-lg font-semibold text-purple-100 light:text-violet-900">
                    Ready for login
                  </h3>
                  <p className={`mt-2 text-sm leading-6 ${bodyMuted}`}>
                    Once verified, you will be redirected to the login page.
                  </p>
                </div>
              </div>
            </section>

            <section
              className={`${formCard} ${cardBorder}`}
            >
              <h2 className={`text-2xl font-semibold ${formHeading}`}>
                Verify Email
              </h2>

              <p className={`mt-2 text-sm ${formSub}`}>
                Account:{" "}
                <span className="text-purple-100 light:text-violet-900">
                  {email || "Unknown email"}
                </span>
              </p>

              <div className="mt-8 rounded-2xl border border-[color:var(--c-border-soft)] bg-purple-950/20 p-5 light:bg-[var(--c-callout-muted)]">
                <form onSubmit={handleVerifyCode} className="space-y-4">
                  <div>
                    <label className="mb-2 block text-sm text-purple-300 light:text-violet-700">
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
                      className={`w-full px-4 py-3 text-sm tracking-[0.3em] ${inputField}`}
                    />
                  </div>

                  {status === "loading" && (
                    <div className="flex items-center gap-3">
                      <div className="h-5 w-5 animate-spin rounded-full border-2 border-purple-300/30 border-t-fuchsia-400" />
                      <p className={`text-sm ${bodyMuted}`}>{message}</p>
                    </div>
                  )}

                  {status !== "loading" && message && (
                    <p
                      className={`text-sm font-medium ${
                        status === "success"
                          ? "text-emerald-300"
                          : status === "error"
                            ? "text-red-300"
                            : "text-purple-200 light:text-violet-800"
                      }`}
                    >
                      {message}
                    </p>
                  )}

                  <div className="flex flex-wrap gap-3">
                    <button
                      type="submit"
                      disabled={isSubmitting || !email}
                      className={`inline-flex items-center rounded-xl px-5 py-3 text-sm disabled:cursor-not-allowed ${primaryCta}`}
                    >
                      {isSubmitting ? "Verifying..." : "Verify code"}
                    </button>

                    <button
                      type="button"
                      onClick={handleResendVerification}
                      disabled={isResending || !email}
                      className={`${ghostLinkBtn} px-5 py-3 disabled:cursor-not-allowed disabled:opacity-60`}
                    >
                      {isResending ? "Sending..." : "Resend code"}
                    </button>

                    <Link
                      to="/register"
                      className={`${ghostLinkBtn} px-5 py-3`}
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