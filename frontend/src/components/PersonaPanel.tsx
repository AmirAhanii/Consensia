import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Minus, Plus, ChevronDown, Star, Trash2 } from "lucide-react";
import { Persona, SavedFavoritePersona } from "../types";
import { ICON_OPTIONS } from "../constants/icons";
import { PersonaEditor } from "./persona-panel/PersonaEditor";

import { API_BASE_URL } from "../config.ts";
import { authApiFetch, readResponseJson } from "../apiFetch";
import { clearAuthSession } from "../authHeaders";
import {
  formCard,
  formHeading,
  formSub,
  inputField,
  personaActiveIconBox,
  personaActiveRow,
  personaSmallIconBox,
  primaryCta,
} from "../theme/themeClasses";
import { toast } from "react-toastify";
import { nanoid } from "../utils/nanoid";

type Props = {
  personas: Persona[];
  onAddPersona: (persona: Omit<Persona, "id">) => void;
  onRemovePersona: (id: string) => void;
  onUpdatePersona: (updated: Persona) => void;
  /** When set, blocks adding debaters once this count is reached (debate workspace). */
  maxDebaters?: number;
  /** When true, show favorite star + load saved favorites from the API. */
  isLoggedIn?: boolean;
  /** When true, no outer card chrome (use inside debate page inline shell). */
  embedInShell?: boolean;
};

const PRESETS: Persona[] = [
  {
    id: "preset-junior",
    name: "Junior Software Engineer",
    description:
      "1 year experience, recently graduated, focuses on quick solutions",
    icon: "User",
  },
  {
    id: "preset-senior",
    name: "Senior Software Engineer",
    description:
      "10 years experience, prioritizes scalability and maintainability",
    icon: "UserStar",
  },
];

function inDebate(personas: Persona[], name: string): boolean {
  return personas.some((p) => p.name === name);
}

function samePersonaContent(
  a: { name: string; description: string; icon: string },
  b: { name: string; description: string; icon: string }
): boolean {
  return (
    a.name.trim() === b.name.trim() &&
    a.description.trim() === b.description.trim() &&
    a.icon.trim() === b.icon.trim()
  );
}

function personaInDebateByContent(personas: Persona[], p: Omit<Persona, "id">): boolean {
  return personas.some((x) => samePersonaContent(x, p));
}

function findMatchingFavorite(
  personas: Persona[],
  favorites: SavedFavoritePersona[]
): Map<string, string> {
  const m = new Map<string, string>();
  for (const p of personas) {
    const hit = favorites.find((f) => samePersonaContent(p, f));
    if (hit) m.set(p.id, hit.id);
  }
  return m;
}

type SearchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string };

export const PersonaPanel: React.FC<Props> = ({
  personas,
  onAddPersona,
  onRemovePersona,
  onUpdatePersona,
  maxDebaters,
  isLoggedIn = false,
  embedInShell = false,
}) => {
  const atDebateLimit =
    typeof maxDebaters === "number" && maxDebaters > 0 && personas.length >= maxDebaters;
  const [customPersonas, setCustomPersonas] = useState<Persona[]>([]);
  const [favorites, setFavorites] = useState<SavedFavoritePersona[]>([]);
  const [favoritesLoading, setFavoritesLoading] = useState(false);
  const [favoriteBusyKey, setFavoriteBusyKey] = useState<string | null>(null);
  const [manualName, setManualName] = useState("");
  const [manualDescription, setManualDescription] = useState("");
  const [manualIcon, setManualIcon] = useState("User");
  const [editingPersonaId, setEditingPersonaId] = useState<string | null>(null);
  const [editIcon, setEditIcon] = useState("User");
  const [newPersonaOpen, setNewPersonaOpen] = useState(false);
  const [createTab, setCreateTab] = useState<"manual" | "cv" | "research">("manual");
  const [searchName, setSearchName] = useState("");
  const [searchState, setSearchState] = useState<SearchState>({ status: "idle" });

  const renderIcon = (
    key: string,
    className = "w-5 h-5 text-purple-300 shrink-0"
  ) => {
    const IconEntry = ICON_OPTIONS.find((opt) => opt.name === key);
    const Icon = IconEntry?.Component ?? ICON_OPTIONS[0].Component;
    return <Icon className={className} />;
  };

  const editingPersona =
    editingPersonaId === null
      ? null
      : personas.find((p) => p.id === editingPersonaId) ?? null;

  const favoriteIdByDebatePersonaId = findMatchingFavorite(personas, favorites);

  const refreshFavorites = useCallback(async () => {
    if (!isLoggedIn) {
      setFavorites([]);
      return;
    }
    try {
      setFavoritesLoading(true);
      const res = await authApiFetch("/api/persona-favorites");
      if (res.status === 401) {
        clearAuthSession();
        toast.info("Session expired. Please sign in again.");
        setFavorites([]);
        return;
      }
      const data = (await readResponseJson<SavedFavoritePersona[] | { detail?: string }>(
        res
      ).catch(() => null)) as SavedFavoritePersona[] | { detail?: string } | null;
      if (!res.ok) {
        const msg =
          typeof (data as { detail?: string } | null)?.detail === "string"
            ? (data as { detail: string }).detail
            : "Could not load favorites";
        throw new Error(msg);
      }
      setFavorites(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
      toast.error(e instanceof Error ? e.message : "Could not load favorites");
      setFavorites([]);
    } finally {
      setFavoritesLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    void refreshFavorites();
  }, [refreshFavorites]);

  useEffect(() => {
    if (editingPersona) setEditIcon(editingPersona.icon);
  }, [editingPersona]);

  const toggleFavoritePersona = async (p: Persona) => {
    if (!isLoggedIn) return;
    const existingFavoriteId = favoriteIdByDebatePersonaId.get(p.id);
    const busy = existingFavoriteId ?? p.id;
    setFavoriteBusyKey(busy);
    try {
      if (existingFavoriteId) {
        const res = await authApiFetch(`/api/persona-favorites/${existingFavoriteId}`, {
          method: "DELETE",
        });
        if (!res.ok) {
          const body = (await readResponseJson<{ detail?: string }>(res).catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(body?.detail || `Remove failed (${res.status})`);
        }
        toast.success("Removed from favorites");
      } else {
        const res = await authApiFetch("/api/persona-favorites", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: p.name,
            description: p.description,
            icon: p.icon,
          }),
        });
        const body = (await readResponseJson<SavedFavoritePersona | { detail?: string }>(
          res
        ).catch(() => null)) as SavedFavoritePersona | { detail?: string } | null;
        if (!res.ok) {
          throw new Error(
            typeof (body as { detail?: string } | null)?.detail === "string"
              ? (body as { detail: string }).detail
              : `Save failed (${res.status})`
          );
        }
        toast.success("Saved to favorites");
      }
      await refreshFavorites();
    } catch (e) {
      console.error(e);
      toast.error(e instanceof Error ? e.message : "Favorite action failed");
    } finally {
      setFavoriteBusyKey(null);
    }
  };

  const removeFavoriteRow = async (favoriteId: string) => {
    setFavoriteBusyKey(favoriteId);
    try {
      const res = await authApiFetch(`/api/persona-favorites/${favoriteId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const body = (await readResponseJson<{ detail?: string }>(res).catch(() => null)) as {
          detail?: string;
        } | null;
        throw new Error(body?.detail || `Remove failed (${res.status})`);
      }
      toast.success("Removed from favorites");
      await refreshFavorites();
    } catch (e) {
      console.error(e);
      toast.error(e instanceof Error ? e.message : "Could not remove favorite");
    } finally {
      setFavoriteBusyKey(null);
    }
  };

  const handleManualCreate = () => {
    if (!manualName.trim() || !manualDescription.trim()) return;
    if (atDebateLimit) {
      toast.info(`You can add up to ${maxDebaters} debaters per session.`);
      return;
    }
    const entry: Persona = {
      id: nanoid(),
      name: manualName.trim(),
      description: manualDescription.trim(),
      icon: manualIcon,
    };
    setCustomPersonas((prev) => [...prev, entry]);
    onAddPersona({
      name: entry.name,
      description: entry.description,
      icon: entry.icon,
    });
    toast.success("Persona added to debate");
    setManualName("");
    setManualDescription("");
    setManualIcon("User");
    setNewPersonaOpen(false);
  };

  const applyResearchPersonaPayload = (
    data: { name?: string; title?: string; description?: string },
    options?: { icon?: string }
  ) => {
    if (atDebateLimit) {
      toast.info(`You can add up to ${maxDebaters} debaters per session.`);
      return;
    }
    const personaName = data.title || data.name || "Unnamed Persona";
    const personaDescription = data.description || "No description provided.";
    const icon = options?.icon ?? "User";
    const entry: Persona = {
      id: nanoid(),
      name: personaName,
      description: personaDescription,
      icon,
    };
    setCustomPersonas((prev) => [...prev, entry]);
    onAddPersona({
      name: entry.name,
      description: entry.description,
      icon: entry.icon,
    });
    toast.success("Persona added");
    setSearchName("");
    setSearchState({ status: "idle" });
    setNewPersonaOpen(false);
  };

  const handleSearchResearcher = async () => {
    if (!searchName.trim()) return;
    if (atDebateLimit) {
      toast.info(`You can add up to ${maxDebaters} debaters per session.`);
      return;
    }
    setSearchState({ status: "loading" });
    try {
      const res = await fetch(`${API_BASE_URL}/api/persona/from-researcher`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: searchName.trim() }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed: ${res.status}`);
      }
      const data = await res.json();
      applyResearchPersonaPayload(data);
      setSearchState({ status: "idle" });
    } catch (err) {
      setSearchState({
        status: "error",
        message: err instanceof Error ? err.message : "Search failed.",
      });
    }
  };

  const handleCVUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (atDebateLimit) {
      toast.info(`You can add up to ${maxDebaters} debaters per session.`);
      event.target.value = "";
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE_URL}/api/persona/from-cv`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      const data = await res.json();
      const personaName = data.title || data.name || "Unnamed Persona";
      const personaDescription = data.description || "No description provided.";
      const entry: Persona = {
        id: nanoid(),
        name: personaName,
        description: personaDescription,
        icon: "User",
      };
      setCustomPersonas((prev) => [...prev, entry]);
      onAddPersona({
        name: entry.name,
        description: entry.description,
        icon: entry.icon,
      });
      toast.success("CV persona added to debate");
      setNewPersonaOpen(false);
    } catch (err) {
      console.error(err);
      toast.error("Failed to create persona from CV.");
    } finally {
      event.target.value = "";
    }
  };

  const addPreset = (p: Persona) => {
    if (atDebateLimit) {
      toast.info(`You can add up to ${maxDebaters} debaters per session.`);
      return;
    }
    onAddPersona({ name: p.name, description: p.description, icon: p.icon });
    toast.success(`${p.name.split(" ")[0]} added`);
  };

  const poolToShow = customPersonas.filter(
    (c) =>
      !personas.some((p) => samePersonaContent(p, c)) &&
      !favorites.some((f) => samePersonaContent(f, c))
  );

  const shellClass = embedInShell ? "space-y-5" : formCard;

  const Shell = embedInShell ? "div" : "article";

  return (
    <Shell className={shellClass}>
      {!embedInShell && (
        <div className="flex items-center justify-between">
          <div>
            <h2 className={`text-lg font-semibold ${formHeading}`}>Personas</h2>
            <p className={`text-sm ${formSub}`}>
              Use + and − to change who is in this debate.
            </p>
          </div>
          <span className="rounded-full border border-purple-800/30 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-purple-300/70 light:border-violet-300/60 light:text-violet-700">
            {typeof maxDebaters === "number"
              ? `${personas.length}/${maxDebaters} in debate`
              : `${personas.length} in debate`}
          </span>
        </div>
      )}

      {/* Active debaters */}
      <div className={embedInShell ? "space-y-2" : "mt-5 space-y-2"}>
        {personas.length === 0 ? (
          <p className="rounded-xl border border-purple-800/30 bg-black/30 px-3 py-3 text-center text-sm text-purple-400/90 light:border-violet-300/60 light:bg-[var(--c-surface-hint)] light:text-[var(--c-fg)]">
            No debaters yet — use + below to add presets or create a new persona.
          </p>
        ) : (
          personas.map((persona) => (
            <div key={persona.id}>
              <div className={personaActiveRow}>
                <div className={personaActiveIconBox}>
                  {renderIcon(
                    persona.icon,
                    "w-5 h-5 text-fuchsia-300 light:text-fuchsia-700"
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className={`truncate text-sm font-medium ${formHeading}`}>
                    {persona.name}
                  </p>
                  <p className="line-clamp-1 text-xs text-purple-400/80 light:text-violet-600">
                    {persona.description}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    type="button"
                    title="Remove from debate"
                    onClick={() => {
                      onRemovePersona(persona.id);
                      if (editingPersonaId === persona.id) setEditingPersonaId(null);
                    }}
                    className="flex h-9 w-9 items-center justify-center rounded-full border border-rose-500/35 text-rose-300 transition hover:bg-rose-500/15 hover:text-rose-100"
                  >
                    <Minus className="h-4 w-4" strokeWidth={2.5} />
                  </button>
                  <button
                    type="button"
                    title="Edit"
                    onClick={() =>
                      setEditingPersonaId((id) =>
                        id === persona.id ? null : persona.id
                      )
                    }
                    className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition ${
                      editingPersonaId === persona.id
                        ? "bg-fuchsia-600/30 text-fuchsia-100"
                        : "text-purple-400 hover:bg-purple-800/40 hover:text-purple-100"
                    }`}
                  >
                    Edit
                  </button>
                  {isLoggedIn ? (
                    <button
                      type="button"
                      title={
                        favoriteIdByDebatePersonaId.has(persona.id)
                          ? "Remove from favorites"
                          : "Save to favorites"
                      }
                      disabled={
                        favoriteBusyKey ===
                        (favoriteIdByDebatePersonaId.get(persona.id) ?? persona.id)
                      }
                      onClick={() => void toggleFavoritePersona(persona)}
                      className={`flex h-9 w-9 items-center justify-center rounded-full border transition ${
                        favoriteIdByDebatePersonaId.has(persona.id)
                          ? "border-amber-500/45 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20"
                          : "border-purple-800/40 text-purple-400 hover:border-amber-500/40 hover:bg-amber-500/10 hover:text-amber-200"
                      } disabled:opacity-40`}
                    >
                      <Star
                        className={`h-4 w-4 ${
                          favoriteIdByDebatePersonaId.has(persona.id)
                            ? "fill-amber-300 text-amber-100"
                            : ""
                        }`}
                        strokeWidth={favoriteIdByDebatePersonaId.has(persona.id) ? 0 : 2}
                      />
                    </button>
                  ) : null}
                </div>
              </div>
              <div
                className={`grid transition-[grid-template-rows] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] motion-reduce:transition-none ${
                  editingPersonaId === persona.id ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                }`}
              >
                <div className="min-h-0 overflow-hidden">
                  {editingPersonaId === persona.id && editingPersona && (
                    <div className="mt-2 rounded-xl border border-purple-800/35 bg-black/40 p-3 motion-reduce:animate-none animate-debaters-reveal light:border-[color:var(--c-border)] light:bg-[var(--c-surface-inline)]">
                      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-purple-500 light:text-violet-600">
                        Icon
                      </p>
                      <div className="mb-3 flex flex-wrap gap-1.5">
                        {ICON_OPTIONS.map((opt) => (
                          <button
                            key={opt.name}
                            type="button"
                            onClick={() => setEditIcon(opt.name)}
                            className={`flex h-9 w-9 items-center justify-center rounded-lg border transition-colors duration-200 ${
                              editIcon === opt.name
                                ? "border-fuchsia-500/60 bg-fuchsia-950/40 text-fuchsia-200 light:bg-fuchsia-100 light:text-fuchsia-900"
                                : "border-purple-800/40 bg-black/40 text-purple-300 hover:border-purple-600/50 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-hint)] light:text-[var(--c-fg)]"
                            }`}
                            title={opt.name}
                          >
                            <opt.Component className="h-4 w-4" />
                          </button>
                        ))}
                      </div>
                      <PersonaEditor
                        key={persona.id}
                        persona={editingPersona}
                        icon={editIcon}
                        onOpenIconModal={() => {}}
                        onCancel={() => setEditingPersonaId(null)}
                        onSave={(updated) => {
                          onUpdatePersona(updated);
                          setEditingPersonaId(null);
                        }}
                        renderIcon={renderIcon}
                        showIconButton={false}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Add presets & saved templates */}
      <div className="space-y-2 border-t border-purple-800/25 pt-4 light:border-violet-200/55">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-purple-500/90 light:text-violet-600">
          Add to debate
        </p>
        <div className="space-y-1.5">
          {PRESETS.filter((p) => !inDebate(personas, p.name)).map((p) => (
            <div
              key={p.id}
              className="flex items-center gap-3 rounded-xl border border-purple-800/30 bg-purple-950/20 px-3 py-2 transition-colors duration-200 hover:border-purple-600/35 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-hint)] light:hover:border-[color:var(--c-border-strong)]"
            >
              <div className={personaSmallIconBox}>
                {renderIcon(p.icon, "w-4 h-4 text-purple-200 light:text-violet-800")}
              </div>
              <span className="min-w-0 flex-1 truncate text-sm text-purple-200/90 light:text-violet-900">
                {p.name}
              </span>
              <button
                type="button"
                title={
                  atDebateLimit
                    ? `Maximum ${maxDebaters} debaters per session`
                    : "Add to debate"
                }
                disabled={atDebateLimit}
                onClick={() => addPreset(p)}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-emerald-500/40 text-emerald-300 transition hover:bg-emerald-500/15 hover:text-emerald-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Plus className="h-4 w-4" strokeWidth={2.5} />
              </button>
            </div>
          ))}
          {isLoggedIn ? (
            <>
              <p className="pt-2 text-[11px] font-semibold uppercase tracking-wide text-amber-200/70 light:text-amber-800/90">
                My favorites
              </p>
              {favoritesLoading && favorites.length === 0 ? (
                <p className="rounded-xl border border-purple-800/30 bg-black/25 px-3 py-2 text-xs text-purple-400 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-hint-deep)] light:text-[var(--c-fg)]">
                  Loading favorites…
                </p>
              ) : favorites.length === 0 ? (
                <p className="rounded-xl border border-purple-800/30 bg-black/25 px-3 py-2 text-xs text-purple-400/90 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-hint-deep)] light:text-[var(--c-fg)]">
                  Star a debater above to save them here — then add them to any chat.
                </p>
              ) : (
                <div className="space-y-1.5">
                  {favorites.map((f) => {
                    const inThis = personaInDebateByContent(personas, f);
                    const busy = favoriteBusyKey === f.id;
                    return (
                      <div
                        key={f.id}
                        className="flex items-center gap-2 rounded-xl border border-amber-500/20 bg-amber-950/15 px-3 py-2 transition-colors duration-200 hover:border-amber-500/35 light:border-amber-400/45 light:bg-[var(--c-surface-amber-row)] light:hover:border-amber-500/55"
                      >
                        <div className={personaSmallIconBox}>
                          {renderIcon(f.icon, "w-4 h-4 text-amber-200/90 light:text-amber-800")}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className={`truncate text-sm font-medium ${formHeading}`}>{f.name}</p>
                          <p className="line-clamp-1 text-xs text-purple-400/80 light:text-violet-600">
                            {f.description}
                          </p>
                        </div>
                        {inThis ? (
                          <span className="shrink-0 rounded-md border border-purple-700/50 bg-black/30 px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-purple-400 light:border-[color:var(--c-border-strong)] light:bg-[var(--c-surface-chip)] light:text-[var(--c-fg)]">
                            In debate
                          </span>
                        ) : (
                          <button
                            type="button"
                            title={
                              atDebateLimit
                                ? `Maximum ${maxDebaters} debaters per session`
                                : "Add to debate"
                            }
                            disabled={busy || atDebateLimit}
                            onClick={() => {
                              onAddPersona({
                                name: f.name,
                                description: f.description,
                                icon: f.icon,
                              });
                              toast.success("Added to debate");
                            }}
                            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-emerald-500/40 text-emerald-300 transition hover:bg-emerald-500/15 hover:text-emerald-100 disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            <Plus className="h-4 w-4" strokeWidth={2.5} />
                          </button>
                        )}
                        <button
                          type="button"
                          title="Remove from favorites"
                          disabled={busy}
                          onClick={() => void removeFavoriteRow(f.id)}
                          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-rose-500/35 text-rose-300/90 transition hover:bg-rose-500/15 hover:text-rose-100 disabled:opacity-40"
                        >
                          <Trash2 className="h-4 w-4" strokeWidth={2.25} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <p className="rounded-xl border border-purple-800/25 bg-black/20 px-3 py-2 text-[11px] leading-relaxed text-purple-400/90 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-hint-deep)] light:text-[var(--c-fg)]">
              <Link
                to="/login"
                className="font-medium text-fuchsia-300 underline-offset-2 hover:text-fuchsia-200 light:text-fuchsia-700 light:hover:text-fuchsia-900"
              >
                Log in
              </Link>{" "}
              to save persona templates and reuse them across debates.
            </p>
          )}
          {poolToShow.map((c) => (
            <div
              key={c.id}
              className="flex items-center gap-3 rounded-xl border border-purple-800/30 bg-purple-950/20 px-3 py-2 transition-colors duration-200 hover:border-purple-600/35 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-hint)] light:hover:border-[color:var(--c-border-strong)]"
            >
              <div className={personaSmallIconBox}>
                {renderIcon(c.icon, "w-4 h-4 text-purple-200 light:text-violet-800")}
              </div>
              <span className="min-w-0 flex-1 truncate text-sm text-purple-200/90 light:text-violet-900">
                {c.name}
              </span>
              <button
                type="button"
                title={
                  atDebateLimit
                    ? `Maximum ${maxDebaters} debaters per session`
                    : "Add to debate"
                }
                disabled={atDebateLimit}
                onClick={() =>
                  onAddPersona({
                    name: c.name,
                    description: c.description,
                    icon: c.icon,
                  })
                }
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-emerald-500/40 text-emerald-300 transition hover:bg-emerald-500/15 hover:text-emerald-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Plus className="h-4 w-4" strokeWidth={2.5} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Inline create */}
      <div className="border-t border-purple-800/25 pt-4 light:border-violet-200/55">
        <button
          type="button"
          aria-expanded={newPersonaOpen}
          onClick={() => setNewPersonaOpen((o) => !o)}
          className="flex w-full items-center justify-between rounded-xl border border-purple-800/40 bg-purple-950/25 px-3 py-2.5 text-left text-sm font-medium text-purple-100 transition-all duration-300 ease-out hover:border-fuchsia-500/35 hover:bg-purple-900/30 motion-reduce:transition-none active:scale-[0.99] light:border-violet-300/65 light:bg-violet-100/80 light:text-violet-900 light:hover:bg-violet-200/70"
        >
          <span>New persona</span>
          <ChevronDown
            className={`h-4 w-4 shrink-0 text-purple-400 transition-transform duration-300 ease-out motion-reduce:transition-none light:text-violet-600 ${
              newPersonaOpen ? "rotate-180" : ""
            }`}
          />
        </button>
        <div
          className={`grid transition-[grid-template-rows] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] motion-reduce:transition-none ${
            newPersonaOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
          }`}
        >
          <div
            className="min-h-0 overflow-hidden"
            {...(!newPersonaOpen ? { inert: "" as const } : {})}
          >
            <div
              className={`mt-2 space-y-3 rounded-xl border border-purple-800/35 bg-black/40 p-3 motion-reduce:animate-none light:border-[color:var(--c-border)] light:bg-[var(--c-surface-tabs)] ${
                newPersonaOpen ? "animate-debaters-reveal" : ""
              }`}
            >
            <div className="flex gap-1 rounded-lg border border-purple-800/40 bg-black/50 p-1 light:border-violet-300/60 light:bg-violet-100/80">
              {(
                [
                  ["manual", "Manual"],
                  ["cv", "CV"],
                  ["research", "Researcher"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => {
                    setCreateTab(id);
                    setSearchState({ status: "idle" });
                  }}
                  className={`flex-1 rounded-md py-1.5 text-xs font-medium transition ${
                    createTab === id
                      ? "bg-fuchsia-600/40 text-white light:bg-violet-600 light:text-white"
                      : "text-purple-400 hover:text-purple-200 light:text-violet-600 light:hover:text-violet-900"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {createTab === "manual" && (
              <div className="space-y-2">
                <p className="text-[11px] font-medium text-purple-500 light:text-violet-600">
                  Icon
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {ICON_OPTIONS.map((opt) => (
                    <button
                      key={opt.name}
                      type="button"
                      onClick={() => setManualIcon(opt.name)}
                      className={`flex h-9 w-9 items-center justify-center rounded-lg border transition ${
                        manualIcon === opt.name
                          ? "border-fuchsia-500/60 bg-fuchsia-950/40"
                          : "border-purple-800/40 bg-black/40 hover:border-purple-600/50"
                      }`}
                    >
                      <opt.Component className="h-4 w-4 text-purple-200 light:text-violet-800" />
                    </button>
                  ))}
                </div>
                <input
                  className={inputField}
                  placeholder="Name"
                  value={manualName}
                  onChange={(e) => setManualName(e.target.value)}
                />
                <textarea
                  className={`min-h-[88px] w-full ${inputField}`}
                  placeholder="Description"
                  value={manualDescription}
                  onChange={(e) => setManualDescription(e.target.value)}
                />
                <button
                  type="button"
                  onClick={handleManualCreate}
                  disabled={
                    !manualName.trim() ||
                    !manualDescription.trim() ||
                    atDebateLimit
                  }
                  title={
                    atDebateLimit
                      ? `Maximum ${maxDebaters} debaters per session`
                      : undefined
                  }
                  className={`w-full py-2 text-sm ${primaryCta}`}
                >
                  Add to debate
                </button>
              </div>
            )}

            {createTab === "cv" && (
              <div className="space-y-2">
                <p className={`text-xs ${formSub}`}>
                  PDF or Word — we extract a persona and add them to the debate.
                </p>
                <input
                  id="cv-upload-inline"
                  type="file"
                  accept=".pdf,.doc,.docx"
                  className="hidden"
                  disabled={atDebateLimit}
                  onChange={handleCVUpload}
                />
                <label
                  htmlFor="cv-upload-inline"
                  className={`block w-full rounded-xl border border-purple-700/50 bg-purple-900/30 py-2.5 text-center text-sm font-medium text-purple-100 transition hover:border-fuchsia-500/40 hover:bg-purple-800/40 light:border-[color:var(--c-border-strong)] light:bg-[var(--c-surface-cta-hover)] light:text-[var(--c-fg)] light:hover:bg-[var(--c-surface-press)] ${
                    atDebateLimit
                      ? "cursor-not-allowed opacity-40"
                      : "cursor-pointer"
                  }`}
                  title={
                    atDebateLimit
                      ? `Maximum ${maxDebaters} debaters per session`
                      : undefined
                  }
                >
                  Choose file
                </label>
              </div>
            )}

            {createTab === "research" && (
              <div className="space-y-2">
                <p className={`text-xs ${formSub}`}>
                  Name search → Scholar scrape → persona, then added to the debate.
                </p>
                <input
                  className={inputField}
                  placeholder="e.g. Steffen Herbold"
                  value={searchName}
                  onChange={(e) => setSearchName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearchResearcher()}
                  disabled={searchState.status === "loading"}
                />
                {searchState.status === "loading" && (
                  <p className="flex items-center gap-2 text-xs text-fuchsia-200">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-fuchsia-400" />
                    Building persona…
                  </p>
                )}
                {searchState.status === "error" && (
                  <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-2 py-1.5 text-xs text-rose-200">
                    {searchState.message}
                  </p>
                )}
                <button
                  type="button"
                  onClick={handleSearchResearcher}
                  disabled={
                    !searchName.trim() ||
                    searchState.status === "loading" ||
                    atDebateLimit
                  }
                  title={
                    atDebateLimit
                      ? `Maximum ${maxDebaters} debaters per session`
                      : undefined
                  }
                  className="w-full rounded-xl bg-purple-700 py-2 text-sm font-medium text-white transition hover:bg-purple-600 disabled:opacity-40 light:bg-violet-600 light:hover:bg-violet-700"
                >
                  {searchState.status === "loading" ? "Searching…" : "Search & add"}
                </button>
              </div>
            )}
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
};
