import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronDown, Home, LayoutDashboard, LogOut, User } from "lucide-react";
import { clearAuthSession } from "../authHeaders";

type Props = {
  isLoggedIn: boolean;
  isAdmin?: boolean;
};

export const DebateUserMenu: React.FC<Props> = ({ isLoggedIn, isAdmin = false }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const email =
    typeof localStorage !== "undefined"
      ? localStorage.getItem("consensia_user_email")
      : null;

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  if (!isLoggedIn) {
    return (
      <Link
        to="/login"
        className="rounded-full border border-[color:var(--c-border-soft)] bg-[var(--c-surface-ghost)] px-3 py-1.5 text-xs text-[var(--c-fg-muted)] transition hover:border-[color:var(--c-border-strong)] hover:bg-[var(--c-surface-ghost-hover)] hover:text-[var(--c-fg)] light:bg-[var(--c-surface-chip)] light:text-[var(--c-fg)] light:hover:bg-[var(--c-surface-chip-hover)] sm:text-sm"
      >
        Log in
      </Link>
    );
  }

  return (
    <div ref={ref} className="relative flex justify-end">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex max-w-[min(200px,42vw)] items-center gap-1.5 rounded-full border border-[color:var(--c-border-soft)] bg-[var(--c-surface-ghost)] py-1.5 pl-2.5 pr-2 text-xs text-[var(--c-fg)] transition hover:border-[color:var(--c-border-strong)] hover:bg-[var(--c-surface-ghost-hover)] light:bg-[var(--c-surface-hint)] sm:gap-2 sm:pl-3 sm:pr-2.5 sm:text-sm"
      >
        <User
          className="h-3.5 w-3.5 shrink-0 text-[var(--c-fg-hint)] light:text-violet-700 sm:h-4 sm:w-4"
          aria-hidden
        />
        <span className="min-w-0 truncate font-medium">{email || "Account"}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 text-[var(--c-fg-hint)] transition-transform sm:h-4 sm:w-4 ${
            open ? "rotate-180" : ""
          }`}
          aria-hidden
        />
      </button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 top-[calc(100%+0.35rem)] z-50 min-w-[11.5rem] overflow-hidden rounded-xl border border-[color:var(--c-border)] bg-[var(--c-surface-dropdown)] py-1 shadow-xl shadow-black/40 backdrop-blur-md light:shadow-[color:var(--c-shadow-card)]"
        >
          <Link
            role="menuitem"
            to="/profile"
            onClick={() => setOpen(false)}
            className="group flex items-center gap-2 px-3 py-2 text-sm text-[var(--c-fg)] transition hover:bg-purple-900/40 light:hover:bg-[var(--c-surface-ghost-hover)]"
          >
            <User
              className="h-4 w-4 text-[var(--c-fg-hint)] transition-colors group-hover:text-purple-200 light:text-violet-700 light:group-hover:text-violet-900"
              aria-hidden
            />
            Profile & settings
          </Link>
          {isAdmin ? (
            <Link
              role="menuitem"
              to="/admin"
              onClick={() => setOpen(false)}
              className="group flex items-center gap-2 px-3 py-2 text-sm text-[var(--c-fg)] transition hover:bg-purple-900/40 light:hover:bg-[var(--c-surface-ghost-hover)]"
            >
              <LayoutDashboard
                className="h-4 w-4 text-[var(--c-fg-hint)] transition-colors group-hover:text-purple-200 light:text-violet-700 light:group-hover:text-violet-900"
                aria-hidden
              />
              Admin statistics
            </Link>
          ) : null}
          <Link
            role="menuitem"
            to="/"
            onClick={() => setOpen(false)}
            className="group flex items-center gap-2 px-3 py-2 text-sm text-[var(--c-fg)] transition hover:bg-purple-900/40 light:hover:bg-[var(--c-surface-ghost-hover)]"
          >
            <Home
              className="h-4 w-4 text-[var(--c-fg-hint)] transition-colors group-hover:text-purple-200 light:text-violet-700 light:group-hover:text-violet-900"
              aria-hidden
            />
            Home
          </Link>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              clearAuthSession();
              setOpen(false);
              navigate("/login", { replace: true });
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-rose-300/95 transition hover:bg-rose-950/35 light:text-rose-800 light:hover:bg-rose-100"
          >
            <LogOut className="h-4 w-4 shrink-0" aria-hidden />
            Log out
          </button>
        </div>
      ) : null}
    </div>
  );
};
