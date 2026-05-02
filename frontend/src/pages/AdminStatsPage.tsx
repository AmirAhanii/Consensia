import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowLeft, LayoutDashboard, Search, Shield, ShieldOff } from "lucide-react";
import { toast } from "react-toastify";
import { ThemedToastContainer } from "../components/ThemedToastContainer";
import { authApiFetch, readResponseJson } from "../apiFetch";
import { clearAuthSession, getAccessToken } from "../authHeaders";

type QuotaSlice = {
  debates: number;
  distinct_subjects: number;
  limit_per_subject: number;
  utilization_pct: number;
};

type DailyPoint = {
  day: string;
  signups: number;
  debates_recorded: number;
  sessions_created: number;
};

type AdminUserRow = {
  id: string;
  email: string;
  full_name: string;
  is_email_verified: boolean;
  is_admin: boolean;
  created_at: string;
  auth_providers: string[];
};

export type AdminStatsPayload = {
  generated_at: string;
  users_total: number;
  users_verified: number;
  users_unverified: number;
  users_with_google: number;
  users_with_local: number;
  sessions_total: number;
  sessions_last_7_days: number;
  sessions_last_30_days: number;
  messages_total: number;
  debates_today_total: number;
  debates_last_14_days_total: number;
  quotas_today: Record<string, QuotaSlice>;
  limits: Record<string, number>;
  debate_volume_by_kind_14d: Record<string, number>;
  series_last_14_days: DailyPoint[];
};

const ACCENT = "#2563eb";
const ACCENT_SOFT = "#93c5fd";
const MAGENTA = "#db2777";
const VIOLET = "#7c3aed";
const MINT = "#059669";

const CHART_TOOLTIP = {
  contentStyle: {
    borderRadius: 16,
    border: "none",
    boxShadow: "0 12px 40px rgba(15, 12, 41, 0.15)",
  },
  labelStyle: { fontWeight: 600, color: "#0f172a" },
};

function formatShortDate(isoDay: string) {
  const d = new Date(isoDay + "T12:00:00Z");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function SemiGauge({
  value,
  title,
  subtitle,
  accent,
}: {
  value: number;
  title: string;
  subtitle: string;
  accent: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  const r = 52;
  const cx = 60;
  const cy = 56;
  const arcLen = Math.PI * r;
  const filled = (pct / 100) * arcLen;

  return (
    <div className="flex flex-col items-center justify-center">
      <p className="mb-1 text-center text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
        {title}
      </p>
      <svg width={120} height={78} viewBox="0 0 120 78" className="overflow-visible">
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={10}
          strokeLinecap="round"
        />
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={accent}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${arcLen}`}
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
        <text
          x={cx}
          y={cy - 6}
          textAnchor="middle"
          className="fill-slate-900 text-[22px] font-bold"
          style={{ fontFamily: "inherit" }}
        >
          {pct.toFixed(0)}%
        </text>
      </svg>
      <p className="mt-1 max-w-[11rem] text-center text-[11px] leading-snug text-slate-500">
        {subtitle}
      </p>
    </div>
  );
}

function WhiteCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-[26px] bg-white p-6 text-slate-900 shadow-[0_20px_50px_rgba(15,12,41,0.12)] ${className}`}
    >
      {children}
    </div>
  );
}

function formatInt(n: number) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(n);
}

export default function AdminStatsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<AdminStatsPayload | null>(null);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [meId, setMeId] = useState<string | null>(null);
  const [userSearch, setUserSearch] = useState("");
  const [usersLoading, setUsersLoading] = useState(false);
  const [rowBusy, setRowBusy] = useState<string | null>(null);

  const fetchUsersList = useCallback(async (q: string, opts?: { trackLoading?: boolean }) => {
    const track = opts?.trackLoading !== false;
    if (track) setUsersLoading(true);
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      const qs = params.toString();
      const res = await authApiFetch(`/api/admin/users${qs ? `?${qs}` : ""}`);
      if (res.status === 401) {
        clearAuthSession();
        toast.error("Session expired.");
        navigate("/login", { replace: true });
        return;
      }
      if (res.status === 403) {
        toast.error("Admin access required.");
        navigate("/profile", { replace: true });
        return;
      }
      if (!res.ok) {
        const err = (await readResponseJson<{ detail?: string }>(res).catch(() => ({}))) as {
          detail?: string;
        };
        throw new Error(err.detail || `Could not load users (${res.status})`);
      }
      const data = (await readResponseJson<{ users: AdminUserRow[] }>(res).catch(() => null)) as {
        users?: AdminUserRow[];
      } | null;
      setUsers(Array.isArray(data?.users) ? data!.users : []);
    } catch (e) {
      console.error(e);
      toast.error(e instanceof Error ? e.message : "Could not load users.");
      setUsers([]);
    } finally {
      if (track) setUsersLoading(false);
    }
  }, [navigate]);

  const load = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    try {
      setLoading(true);
      const [statsRes, meRes] = await Promise.all([
        authApiFetch("/api/admin/stats"),
        authApiFetch("/api/auth/me"),
      ]);

      const statsData = (await readResponseJson(statsRes).catch(() => null)) as
        | AdminStatsPayload
        | { detail?: string }
        | null;

      if (statsRes.status === 401) {
        clearAuthSession();
        toast.error("Session expired.");
        navigate("/login", { replace: true });
        return;
      }
      if (statsRes.status === 403) {
        toast.error("Admin access required.");
        navigate("/profile", { replace: true });
        return;
      }
      if (
        !statsRes.ok ||
        !statsData ||
        typeof statsData !== "object" ||
        !("users_total" in statsData)
      ) {
        throw new Error(
          (statsData as { detail?: string } | null)?.detail ||
            `Could not load stats (${statsRes.status})`
        );
      }
      setStats(statsData as AdminStatsPayload);

      if (meRes.ok) {
        const me = (await readResponseJson<{ id?: string }>(meRes).catch(() => null)) as {
          id?: string;
        } | null;
        setMeId(me?.id ?? null);
      } else {
        setMeId(null);
      }
    } catch (e) {
      console.error(e);
      toast.error(e instanceof Error ? e.message : "Could not load admin statistics.");
      navigate("/profile", { replace: true });
    } finally {
      setLoading(false);
    }
  }, [navigate, fetchUsersList]);

  const patchUserAdmin = useCallback(
    async (userId: string, is_admin: boolean) => {
      setRowBusy(userId);
      try {
        const res = await authApiFetch(`/api/admin/users/${userId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_admin }),
        });
        const errBody = (await readResponseJson<{ detail?: string }>(res).catch(() => ({}))) as {
          detail?: string;
        };
        if (!res.ok) {
          throw new Error(errBody.detail || `Update failed (${res.status})`);
        }
        toast.success(is_admin ? "Admin access granted." : "Admin access removed.");
        await fetchUsersList(userSearch, { trackLoading: true });
      } catch (e) {
        console.error(e);
        toast.error(e instanceof Error ? e.message : "Could not update user.");
      } finally {
        setRowBusy(null);
      }
    },
    [fetchUsersList, userSearch]
  );

  useEffect(() => {
    if (!stats) return;
    const q = userSearch.trim();
    const delay = q.length === 0 ? 0 : 400;
    const t = window.setTimeout(() => {
      void fetchUsersList(userSearch, { trackLoading: delay > 0 });
    }, delay);
    return () => window.clearTimeout(t);
  }, [userSearch, stats, fetchUsersList]);

  useEffect(() => {
    document.title = "Consensia — Admin statistics";
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const lineData = useMemo(() => {
    if (!stats) return [];
    return stats.series_last_14_days.map((row) => ({
      label: formatShortDate(row.day),
      signups: row.signups,
      debates: row.debates_recorded,
      sessions: row.sessions_created,
    }));
  }, [stats]);

  const verifiedPie = useMemo(() => {
    if (!stats) return [];
    return [
      { name: "Verified email", value: stats.users_verified, color: ACCENT },
      { name: "Unverified", value: stats.users_unverified, color: MAGENTA },
    ].filter((x) => x.value > 0);
  }, [stats]);

  const authPie = useMemo(() => {
    if (!stats) return [];
    return [
      { name: "Google sign-in", value: stats.users_with_google, color: VIOLET },
      { name: "Email / password", value: stats.users_with_local, color: ACCENT_SOFT },
    ].filter((x) => x.value > 0);
  }, [stats]);

  const debateKindPie = useMemo(() => {
    if (!stats) return [];
    const m = stats.debate_volume_by_kind_14d;
    return [
      { name: "Signed-in users", value: m.user ?? 0, color: ACCENT },
      { name: "Guests (anon)", value: m.anon ?? 0, color: MAGENTA },
    ].filter((x) => x.value > 0);
  }, [stats]);

  const anonQ = stats?.quotas_today?.anon;
  const userQ = stats?.quotas_today?.user;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f0c29] via-[#1a1a2e] to-[#121c3b] text-slate-100">
      <ThemedToastContainer position="top-center" autoClose={4000} />
      <div className="mx-auto max-w-[1280px] px-4 pb-16 pt-8 sm:px-6 lg:px-8">
        <header className="mb-10 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-xs font-medium text-white/90 backdrop-blur">
                <LayoutDashboard className="h-3.5 w-3.5 opacity-80" aria-hidden />
                Admin
              </span>
              <span className="rounded-full border border-white/10 px-4 py-1.5 text-xs text-white/60">
                Overview
              </span>
            </div>
            <h1 className="mt-5 text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Workspace statistics
            </h1>
            <p className="mt-2 max-w-xl text-sm text-white/55">
              Usage, quota pressure, and growth — same visual language as your analytics
              dashboards: light cards on a deep field.
            </p>
          </div>
          <Link
            to="/profile"
            className="inline-flex items-center gap-2 self-start rounded-full border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white/90 transition hover:bg-white/10"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Back to profile
          </Link>
        </header>

        {loading ? (
          <p className="text-center text-sm text-white/50">Loading statistics…</p>
        ) : stats ? (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
            {/* Hero + gauges row */}
            <WhiteCard className="lg:col-span-3 flex flex-col justify-between bg-gradient-to-br from-[#2563eb] to-[#1d4ed8] !p-6 text-white shadow-none">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">
                  Registered users
                </p>
                <p className="mt-3 text-4xl font-bold tabular-nums sm:text-5xl">
                  {formatInt(stats.users_total)}
                </p>
              </div>
              <p className="mt-6 text-xs leading-relaxed text-white/75">
                {formatInt(stats.users_verified)} verified · {formatInt(stats.users_unverified)}{" "}
                pending verification
              </p>
            </WhiteCard>

            <WhiteCard className="lg:col-span-3 flex items-center justify-center">
              <SemiGauge
                value={anonQ?.utilization_pct ?? 0}
                title="Guest quota (UTC today)"
                subtitle={`${formatInt(anonQ?.debates ?? 0)} debates · ${formatInt(anonQ?.distinct_subjects ?? 0)} guest keys · cap ${anonQ?.limit_per_subject ?? "—"}/key`}
                accent={MAGENTA}
              />
            </WhiteCard>

            <WhiteCard className="lg:col-span-3 flex items-center justify-center">
              <SemiGauge
                value={userQ?.utilization_pct ?? 0}
                title="User quota (UTC today)"
                subtitle={`${formatInt(userQ?.debates ?? 0)} debates · ${formatInt(userQ?.distinct_subjects ?? 0)} accounts active · cap ${userQ?.limit_per_subject ?? "—"}/account`}
                accent={ACCENT}
              />
            </WhiteCard>

            <WhiteCard className="lg:col-span-3 flex min-h-[220px] flex-col">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Email verification
              </p>
              <div className="mt-2 flex flex-1 flex-col">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={verifiedPie.length ? verifiedPie : [{ name: "No users", value: 1, color: "#e2e8f0" }]}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={54}
                      outerRadius={78}
                      paddingAngle={2}
                    >
                      {verifiedPie.length ? (
                        verifiedPie.map((e, i) => <Cell key={i} fill={e.color} />)
                      ) : (
                        <Cell fill="#e2e8f0" />
                      )}
                    </Pie>
                    <Tooltip {...CHART_TOOLTIP} formatter={(v: number) => formatInt(v)} />
                    <Legend verticalAlign="bottom" height={28} iconType="circle" />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </WhiteCard>

            {/* Growth line */}
            <WhiteCard className="lg:col-span-8">
              <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Growth & activity
                  </p>
                  <h2 className="mt-1 text-lg font-bold text-slate-900">Last 14 days</h2>
                </div>
                <p className="max-w-sm text-right text-xs leading-relaxed text-slate-500">
                  Signups vs quota-metered debates vs new saved sessions. Peaks often track
                  launches or classroom demos.
                </p>
              </div>
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={lineData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="4 8" stroke="#e2e8f0" vertical={false} />
                    <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} width={36} />
                    <Tooltip {...CHART_TOOLTIP} />
                    <Legend iconType="circle" />
                    <Line
                      type="monotone"
                      dataKey="signups"
                      name="Signups"
                      stroke={ACCENT}
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 5 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="debates"
                      name="Debates (metered)"
                      stroke={MAGENTA}
                      strokeWidth={2.5}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="sessions"
                      name="Sessions created"
                      stroke={MINT}
                      strokeWidth={2}
                      strokeDasharray="6 4"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </WhiteCard>

            {/* Side column donuts */}
            <div className="flex flex-col gap-5 lg:col-span-4">
              <WhiteCard className="min-h-[200px] flex-1">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Debate volume (14d)
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-800">By audience</p>
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={
                          debateKindPie.length
                            ? debateKindPie
                            : [{ name: "No debates", value: 1, color: "#e2e8f0" }]
                        }
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={48}
                        outerRadius={72}
                        paddingAngle={2}
                      >
                        {debateKindPie.length ? (
                          debateKindPie.map((e, i) => <Cell key={i} fill={e.color} />)
                        ) : (
                          <Cell fill="#e2e8f0" />
                        )}
                      </Pie>
                      <Tooltip {...CHART_TOOLTIP} formatter={(v: number) => formatInt(v)} />
                      <Legend verticalAlign="bottom" height={28} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </WhiteCard>

              <WhiteCard className="min-h-[200px] flex-1">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Auth identities
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-800">Distinct users per provider</p>
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={authPie.length ? authPie : [{ name: "No identities", value: 1, color: "#e2e8f0" }]}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={48}
                        outerRadius={72}
                        paddingAngle={2}
                      >
                        {authPie.length ? (
                          authPie.map((e, i) => <Cell key={i} fill={e.color} />)
                        ) : (
                          <Cell fill="#e2e8f0" />
                        )}
                      </Pie>
                      <Tooltip {...CHART_TOOLTIP} formatter={(v: number) => formatInt(v)} />
                      <Legend verticalAlign="bottom" height={28} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </WhiteCard>
            </div>

            {/* Bottom stat strip */}
            <div className="contents lg:contents">
              <WhiteCard className="lg:col-span-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Sessions</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">{formatInt(stats.sessions_total)}</p>
                <p className="mt-2 text-xs text-slate-500">
                  {formatInt(stats.sessions_last_7_days)} in last 7 days ·{" "}
                  {formatInt(stats.sessions_last_30_days)} in last 30 days
                </p>
              </WhiteCard>
              <WhiteCard className="lg:col-span-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Messages</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">{formatInt(stats.messages_total)}</p>
                <p className="mt-2 text-xs text-slate-500">All roles stored on debates</p>
              </WhiteCard>
              <WhiteCard className="lg:col-span-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Debates today</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">
                  {formatInt(stats.debates_today_total)}
                </p>
                <p className="mt-2 text-xs text-slate-500">Quota buckets (UTC), incl. guest + user</p>
              </WhiteCard>
              <WhiteCard className="lg:col-span-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Debates (14d)</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">
                  {formatInt(stats.debates_last_14_days_total)}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Updated {new Date(stats.generated_at).toLocaleString()}
                </p>
              </WhiteCard>
            </div>

            <WhiteCard className="lg:col-span-12">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    User management
                  </p>
                  <h2 className="mt-1 text-lg font-bold text-slate-900">Accounts</h2>
                  <p className="mt-1 max-w-xl text-xs text-slate-500">
                    Grant or revoke workspace admin (same as <code className="rounded bg-slate-100 px-1">is_admin</code>{" "}
                    in the database). You cannot remove admin from yourself here.
                  </p>
                </div>
                <div className="relative w-full sm:max-w-xs">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                    aria-hidden
                  />
                  <input
                    type="search"
                    value={userSearch}
                    onChange={(e) => setUserSearch(e.target.value)}
                    placeholder="Search email or name…"
                    className="w-full rounded-2xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none ring-slate-300 placeholder:text-slate-400 focus:ring-2"
                  />
                </div>
              </div>

              <div className="mt-4 overflow-x-auto rounded-2xl border border-slate-100">
                <table className="min-w-[720px] w-full border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/80 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      <th className="px-4 py-3">User</th>
                      <th className="px-4 py-3">Email</th>
                      <th className="px-4 py-3">Verified</th>
                      <th className="px-4 py-3">Auth</th>
                      <th className="px-4 py-3">Joined</th>
                      <th className="px-4 py-3 text-right">Admin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersLoading && users.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                          Loading users…
                        </td>
                      </tr>
                    ) : users.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                          No users match this search.
                        </td>
                      </tr>
                    ) : (
                      users.map((u) => {
                        const isSelf = Boolean(meId && u.id === meId);
                        const busy = rowBusy === u.id;
                        return (
                          <tr key={u.id} className="border-b border-slate-50 last:border-0">
                            <td className="px-4 py-3 font-medium text-slate-900">
                              <span className="line-clamp-2" title={u.full_name}>
                                {u.full_name}
                              </span>
                            </td>
                            <td className="max-w-[220px] px-4 py-3 text-slate-600">
                              <span className="block truncate" title={u.email}>
                                {u.email}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-slate-600">
                              {u.is_email_verified ? (
                                <span className="text-emerald-600">Yes</span>
                              ) : (
                                <span className="text-amber-600">No</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-slate-600">
                              {u.auth_providers.length ? u.auth_providers.join(", ") : "—"}
                            </td>
                            <td className="whitespace-nowrap px-4 py-3 text-slate-500">
                              {new Date(u.created_at).toLocaleDateString(undefined, {
                                year: "numeric",
                                month: "short",
                                day: "numeric",
                              })}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {u.is_admin ? (
                                <div className="flex flex-wrap items-center justify-end gap-2">
                                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-800">
                                    <Shield className="h-3.5 w-3.5" aria-hidden />
                                    Admin
                                    {isSelf ? " · you" : ""}
                                  </span>
                                  {!isSelf ? (
                                    <button
                                      type="button"
                                      disabled={busy}
                                      onClick={() => void patchUserAdmin(u.id, false)}
                                      className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                                    >
                                      <ShieldOff className="h-3.5 w-3.5" aria-hidden />
                                      {busy ? "…" : "Revoke"}
                                    </button>
                                  ) : null}
                                </div>
                              ) : (
                                <button
                                  type="button"
                                  disabled={busy}
                                  onClick={() => void patchUserAdmin(u.id, true)}
                                  className="inline-flex items-center gap-1 rounded-full bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50"
                                >
                                  <Shield className="h-3.5 w-3.5" aria-hidden />
                                  {busy ? "…" : "Make admin"}
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
              {usersLoading && users.length > 0 ? (
                <p className="mt-2 text-center text-xs text-slate-400">Updating list…</p>
              ) : null}
            </WhiteCard>
          </div>
        ) : null}
      </div>
    </div>
  );
}
