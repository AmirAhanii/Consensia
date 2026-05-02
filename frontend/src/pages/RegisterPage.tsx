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
import { apiFetch, readResponseJson } from "../apiFetch";

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

      // First hit after Render sleep can spend a long time in startup/migrations before the handler runs.
      const response = await apiFetch(
        "/api/auth/register",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            full_name: fullName.trim(),
            email: email.trim(),
            password,
          }),
        },
        240_000
      );

      const data = (await readResponseJson<ApiErrorResponse>(response).catch(
        () => null
      )) as ApiErrorResponse | null;

      if (!response.ok) {
        throw new Error(
          formatApiDetail(data?.detail) ||
            data?.message ||
            `Registration failed (${response.status})`
        );
      }

      toast.success(
        data?.message ||
          "Registration successful. Please check your email to verify your account."
      );

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
                Join Consensia
              </p>

              <h1
                className={`mt-4 bg-gradient-to-br bg-clip-text text-5xl font-bold tracking-tight text-transparent md:text-6xl ${heroTitleGradient}`}
              >
                Create your account
              </h1>

              <p className={`mt-6 max-w-2xl text-lg leading-relaxed ${bodyMuted}`}>
                Register to access the prototype workspace, create personas, run
                debates, and explore judge-generated consensus for
                software-engineering decision making.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <div className={promoCard}>
                  <h3 className="text-lg font-semibold text-purple-100 light:text-violet-900">
                    Multi-persona debates
                  </h3>
                  <p className={`mt-2 text-sm leading-6 ${bodyMuted}`}>
                    Compare viewpoints from multiple software-engineering roles.
                  </p>
                </div>

                <div className={promoCard}>
                  <h3 className="text-lg font-semibold text-purple-100 light:text-violet-900">
                    Judge synthesis
                  </h3>
                  <p className={`mt-2 text-sm leading-6 ${bodyMuted}`}>
                    Review a final summary and reasoning generated from the
                    debate.
                  </p>
                </div>
              </div>
            </section>

            <section className={formCard}>
              <h2 className={`text-2xl font-semibold ${formHeading}`}>Register</h2>
              <p className={`mt-2 text-sm ${formSub}`}>
                Create an account to start using the prototype.
              </p>

              <form onSubmit={handleRegister} className="mt-6 space-y-4">
                <div>
                  <label className="mb-2 block text-sm text-purple-300 light:text-violet-700">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Enter your full name"
                    className={`w-full px-4 py-3 text-sm ${inputField}`}
                  />
                </div>

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
                    Institution / Company
                  </label>
                  <input
                    type="text"
                    value={institution}
                    onChange={(e) => setInstitution(e.target.value)}
                    placeholder="Optional"
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
                    placeholder="Create a password"
                    className={`w-full px-4 py-3 text-sm ${inputField}`}
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm text-purple-300 light:text-violet-700">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm your password"
                    className={`w-full px-4 py-3 text-sm ${inputField}`}
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={`w-full px-6 py-3 text-sm disabled:cursor-not-allowed ${primaryCta}`}
                >
                  {isSubmitting ? "Creating account..." : "Sign Up"}
                </button>
              </form>

              <p className={`mt-5 text-center text-sm text-purple-300/75 light:text-violet-600`}>
                Already have an account?{" "}
                <Link
                  to="/login"
                  className="text-purple-100 underline underline-offset-4 hover:text-white light:text-violet-800"
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