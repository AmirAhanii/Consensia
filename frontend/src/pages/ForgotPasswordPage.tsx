import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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

type Step = "email" | "code" | "password";

type ApiErrorResponse = {
  detail?: string;
  message?: string;
};

export default function ForgotPasswordPage() {
  const navigate = useNavigate();

  useEffect(() => {
    document.title = "Consensia — Reset password";
  }, []);

  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSendingCode, setIsSendingCode] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [isVerifyingCode, setIsVerifyingCode] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  const sendCode = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) {
      toast.error("Please enter your email.");
      return;
    }

    try {
      setIsSendingCode(true);
      const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: trimmed }),
      });
      const data = (await response.json().catch(() => null)) as
        | ApiErrorResponse
        | { message?: string }
        | null;

      if (!response.ok) {
        throw new Error(
          (data as ApiErrorResponse | null)?.detail ||
            (data as ApiErrorResponse | null)?.message ||
            `Request failed (${response.status})`,
        );
      }

      toast.success(
        (data as { message?: string } | null)?.message ||
          "If that account supports password reset, check your email for a code.",
      );
      setStep("code");
    } catch (err) {
      console.error(err);
      toast.error(
        err instanceof Error ? err.message : "Could not send reset instructions.",
      );
    } finally {
      setIsSendingCode(false);
    }
  };

  const resendCode = async () => {
    const trimmed = email.trim();
    if (!trimmed) return;
    try {
      setIsResending(true);
      const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: trimmed }),
      });
      const data = (await response.json().catch(() => null)) as ApiErrorResponse | null;
      if (!response.ok) {
        throw new Error(
          data?.detail || data?.message || `Resend failed (${response.status})`,
        );
      }
      toast.success("A new code has been sent if your account supports password reset.");
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Could not resend code.");
    } finally {
      setIsResending(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedEmail = email.trim();
    const trimmedCode = code.trim();
    if (!/^\d{6}$/.test(trimmedCode)) {
      toast.error("Enter the 6-digit code from your email.");
      return;
    }

    try {
      setIsVerifyingCode(true);
      const response = await fetch(
        `${API_BASE_URL}/api/auth/verify-password-reset-code`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: trimmedEmail,
            code: trimmedCode,
          }),
        },
      );
      const data = (await response.json().catch(() => null)) as ApiErrorResponse | null;
      if (!response.ok) {
        throw new Error(
          data?.detail || data?.message || `Verification failed (${response.status})`,
        );
      }
      toast.success("Code verified. Choose your new password.");
      setStep("password");
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Invalid or expired code.");
    } finally {
      setIsVerifyingCode(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedEmail = email.trim();
    const trimmedCode = code.trim();
    if (!/^\d{6}$/.test(trimmedCode)) {
      toast.error("Enter the 6-digit code from your email.");
      return;
    }
    if (newPassword.length < 6) {
      toast.error("New password must be at least 6 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("New password and confirmation do not match.");
      return;
    }

    try {
      setIsResetting(true);
      const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: trimmedEmail,
          code: trimmedCode,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });
      const data = (await response.json().catch(() => null)) as ApiErrorResponse | null;
      if (!response.ok) {
        throw new Error(
          data?.detail || data?.message || `Reset failed (${response.status})`,
        );
      }
      toast.success("Password updated. You can log in with your new password.");
      navigate("/login", { replace: true });
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Could not reset password.");
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <>
      <GradientBackground />
      <ThemedToastContainer position="top-center" autoClose={4000} />

      <div className={`relative z-10 min-h-screen px-6 py-10 ${pageShell}`}>
        <div className="mx-auto max-w-6xl">
          <Link to="/" className={ghostLinkBtn}>
            ← Back to Homepage
          </Link>

          <div className="mt-10 grid gap-10 lg:grid-cols-[1.05fr_0.95fr]">
            <section className="flex flex-col justify-center">
              <p
                className={`text-sm font-semibold uppercase tracking-[0.2em] ${eyebrowMuted}`}
              >
                Account recovery
              </p>

              <h1
                className={`mt-4 bg-gradient-to-br bg-clip-text text-5xl font-bold tracking-tight text-transparent md:text-6xl ${heroTitleGradient}`}
              >
                Reset your password
              </h1>

              <p className={`mt-6 max-w-2xl text-lg leading-relaxed ${bodyMuted}`}>
                Enter your email to receive a code, confirm the 6-digit code, then
                set a new password—only after the code checks out do we show the
                password fields.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <div className={promoCard}>
                  <h3 className="text-lg font-semibold text-purple-100 light:text-violet-900">
                    Email-only accounts
                  </h3>
                  <p className={`mt-2 text-sm leading-6 ${bodyMuted}`}>
                    Password reset applies to accounts that use email and password.
                    Google-only sign-in does not use a Consensia password here.
                  </p>
                </div>

                <div className={promoCard}>
                  <h3 className="text-lg font-semibold text-purple-100 light:text-violet-900">
                    Same inbox as signup
                  </h3>
                  <p className={`mt-2 text-sm leading-6 ${bodyMuted}`}>
                    Codes work like email verification: 6 digits, 24-hour expiry.
                    You can resend a new code from this page.
                  </p>
                </div>
              </div>
            </section>

            <section className={formCard}>
              <h2 className={`text-2xl font-semibold ${formHeading}`}>
                {step === "email"
                  ? "Request reset code"
                  : step === "code"
                    ? "Enter verification code"
                    : "New password"}
              </h2>
              <p className={`mt-2 text-sm ${formSub}`}>
                {step === "email"
                  ? "We will email a verification code if this address can reset a password."
                  : `Using: ${email.trim() || "—"}`}
              </p>

              <div className="mt-8 rounded-2xl border border-[color:var(--c-border-soft)] bg-purple-950/20 p-5 light:bg-[var(--c-callout-muted)]">
                {step === "email" ? (
                  <form onSubmit={sendCode} className="space-y-4">
                    <div>
                      <label className="mb-2 block text-sm text-purple-300 light:text-violet-700">
                        Email
                      </label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                        autoComplete="email"
                        className={`w-full px-4 py-3 text-sm ${inputField}`}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={isSendingCode}
                      className={`w-full px-6 py-3 text-sm disabled:cursor-not-allowed ${primaryCta}`}
                    >
                      {isSendingCode ? "Sending…" : "Send code"}
                    </button>
                  </form>
                ) : step === "code" ? (
                  <form onSubmit={handleVerifyCode} className="space-y-4">
                    <div>
                      <label className="mb-2 block text-sm text-purple-300 light:text-violet-700">
                        6-digit code
                      </label>
                      <input
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        value={code}
                        onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                        placeholder="Enter code"
                        className={`w-full px-4 py-3 text-sm tracking-[0.3em] ${inputField}`}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={isVerifyingCode}
                      className={`w-full px-6 py-3 text-sm disabled:cursor-not-allowed ${primaryCta}`}
                    >
                      {isVerifyingCode ? "Checking…" : "Verify code"}
                    </button>
                    <div className="flex flex-wrap gap-3 pt-1">
                      <button
                        type="button"
                        onClick={resendCode}
                        disabled={isResending}
                        className={`${ghostLinkBtn} px-1 py-2 disabled:cursor-not-allowed disabled:opacity-60`}
                      >
                        {isResending ? "Sending…" : "Resend code"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setStep("email");
                          setCode("");
                          setNewPassword("");
                          setConfirmPassword("");
                        }}
                        className={`${ghostLinkBtn} px-1 py-2`}
                      >
                        Different email
                      </button>
                    </div>
                  </form>
                ) : (
                  <form onSubmit={handleResetPassword} className="space-y-4">
                    <div>
                      <label className="mb-2 block text-sm text-purple-300 light:text-violet-700">
                        New password
                      </label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="At least 6 characters"
                        autoComplete="new-password"
                        className={`w-full px-4 py-3 text-sm ${inputField}`}
                      />
                    </div>
                    <div>
                      <label className="mb-2 block text-sm text-purple-300 light:text-violet-700">
                        Confirm new password
                      </label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Repeat new password"
                        autoComplete="new-password"
                        className={`w-full px-4 py-3 text-sm ${inputField}`}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={isResetting}
                      className={`w-full px-6 py-3 text-sm disabled:cursor-not-allowed ${primaryCta}`}
                    >
                      {isResetting ? "Updating…" : "Update password"}
                    </button>
                    <div className="pt-1">
                      <button
                        type="button"
                        onClick={() => {
                          setStep("code");
                          setNewPassword("");
                          setConfirmPassword("");
                        }}
                        className={`${ghostLinkBtn} px-1 py-2`}
                      >
                        Change code
                      </button>
                    </div>
                  </form>
                )}
              </div>

              <p className={`mt-5 text-center text-sm text-purple-300/75 light:text-violet-600`}>
                Remember your password?{" "}
                <Link
                  to="/login"
                  className="text-purple-100 underline underline-offset-4 light:text-violet-800"
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
