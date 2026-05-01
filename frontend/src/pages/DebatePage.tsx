import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { authHeaders, clearAuthSession, getAccessToken } from "../authHeaders";
import { DebateUserMenu } from "../components/DebateUserMenu";
import { GradientBackground } from "../components/GradientBackground";
import { DebateChatThread } from "../components/DebateChatThread";
import { DebateComposer } from "../components/DebateComposer";
import { PersonaPanel } from "../components/PersonaPanel";
import { SessionSidebar, type DebateSessionItem } from "../components/SessionSidebar";
import { API_BASE_URL, MAX_DEBATERS_PER_SESSION } from "../config";
import { DebateMessage, DebateResult, Persona, PersonaCalibrationScore } from "../types";
import { nanoid } from "../utils/nanoid";
import { debateResultFromStored } from "../utils/debateResultFromStored";
import { ThemedToastContainer } from "../components/ThemedToastContainer";
import { toast } from "react-toastify";
import {
  debateDebatersPanel,
  debateDebatersPanelHeader,
  debateDebatersToggleBtn,
  debateDockStrip,
  formHeading,
  pageShell,
  stickyHeader,
} from "../theme/themeClasses";

type ApiPersonaAnswer = {
  persona_id: string;
  persona_name: string;
  persona_description: string;
  answer: string;
};

type ApiQaRow = {
  persona_id: string;
  persona_name: string;
  score: number;
  rationale: string;
};

type ApiDebateResponse = {
  rounds: {
    round_number: number;
    label: string;
    persona_answers: ApiPersonaAnswer[];
  }[];
  topic_relevance_qa?: ApiQaRow[];
  reasoning_quality_qa?: ApiQaRow[];
  judge: { summary: string; reasoning: string };
};

function mapCalibrationRows(rows: ApiQaRow[] | undefined): PersonaCalibrationScore[] {
  if (!Array.isArray(rows)) return [];
  return rows.map((row) => ({
    personaId: row.persona_id,
    personaName: row.persona_name,
    score: Number.isFinite(row.score) ? Math.max(0, Math.min(9, Math.round(row.score))) : 0,
    rationale: typeof row.rationale === "string" ? row.rationale : "",
  }));
}

const DEFAULT_PERSONAS: Persona[] = [
  {
    id: nanoid(),
    name: "Junior Software Engineer",
    description: "1 year experience, recently graduated, focuses on quick solutions",
    icon: "User",
  },
  {
    id: nanoid(),
    name: "Senior Software Engineer",
    description: "10 years experience, prioritizes scalability and maintainability",
    icon: "UserStar",
  },
];

function sessionTitle(question: string): string {
  const q = question.trim();
  return q.length > 60 ? q.slice(0, 60) + "…" : q || "New Debate";
}

type DebatersBlockProps = {
  debatersOpen: boolean;
  setDebatersOpen: React.Dispatch<React.SetStateAction<boolean>>;
  isLoggedIn: boolean;
  personas: Persona[];
  maxDebaters: number;
  onAddPersona: (persona: Omit<Persona, "id">) => void;
  onRemovePersona: (id: string) => void;
  onUpdatePersona: (persona: Persona) => void;
  placement?: "below" | "above";
};

function DebatersBlock({
  debatersOpen,
  setDebatersOpen,
  isLoggedIn,
  personas,
  maxDebaters,
  onAddPersona,
  onRemovePersona,
  onUpdatePersona,
  placement = "below",
}: DebatersBlockProps) {
  return (
    <div className="mx-auto w-full max-w-3xl px-3 sm:px-4">
      <div className={`flex ${placement === "above" ? "flex-col-reverse" : "flex-col"}`}>
        <div className="flex justify-center py-2">
          <button
            type="button"
            aria-expanded={debatersOpen}
            onClick={() => setDebatersOpen((o) => !o)}
            className={debateDebatersToggleBtn}
          >
            Debaters · {personas.length}/{maxDebaters} persona{personas.length !== 1 ? "s" : ""}
            <ChevronDown
              className={`h-3.5 w-3.5 shrink-0 text-purple-500 transition-transform duration-300 ease-out motion-reduce:transition-none light:text-violet-600 ${
                debatersOpen ? "rotate-180" : ""
              }`}
              aria-hidden
            />
          </button>
        </div>
        <div
          className={`grid transition-[grid-template-rows] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] motion-reduce:transition-none ${
            debatersOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
          }`}
        >
          <div className="min-h-0 overflow-hidden">
            <div
              className={`${debateDebatersPanel} motion-reduce:animate-none ${
                debatersOpen ? "animate-debaters-reveal" : ""
              }`}
            >
              <div
                className="pointer-events-none absolute inset-0 overflow-hidden rounded-3xl"
                aria-hidden
              >
                <div className="absolute -left-4 top-0 h-40 w-40 rounded-full bg-purple-400/12 blur-2xl" />
                <div className="absolute -right-8 top-1/4 h-36 w-36 -translate-y-1/2 rounded-full bg-fuchsia-500/10 blur-2xl" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(167,139,250,0.08),transparent_50%)]" />
              </div>
              <div className={debateDebatersPanelHeader}>
                <p className="bg-gradient-to-r from-[#F5F3FF] to-[#C7B8FF] bg-clip-text text-sm font-bold tracking-tight text-transparent light:from-violet-800 light:to-fuchsia-700">
                  Debaters
                </p>
                <p className="mt-0.5 text-xs text-purple-300/70 light:text-violet-600/85">
                  {personas.length} active (max {maxDebaters}) · presets, favorites, CV, or researcher
                </p>
              </div>
              <div className="relative px-4 pb-4 pt-2 sm:px-5 sm:pb-5">
                <PersonaPanel
                  embedInShell
                  isLoggedIn={isLoggedIn}
                  personas={personas}
                  maxDebaters={maxDebaters}
                  onAddPersona={onAddPersona}
                  onRemovePersona={onRemovePersona}
                  onUpdatePersona={onUpdatePersona}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DebatePage() {
  useEffect(() => {
    document.title = "Consensia App — Debate Workspace";
  }, []);

  const [isLoggedIn, setIsLoggedIn] = useState(Boolean(getAccessToken()));
  useEffect(() => {
    const sync = () => setIsLoggedIn(Boolean(getAccessToken()));
    window.addEventListener("storage", sync);
    window.addEventListener("consensia-auth-changed", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("consensia-auth-changed", sync);
    };
  }, []);

  const [personas, setPersonas] = useState<Persona[]>(DEFAULT_PERSONAS);
  // `composerText` is what the user is currently typing.
  const [composerText, setComposerText] = useState("");
  // `threadQuestion` is the selected session's question (display-only; does not prefill composer).
  const [threadQuestion, setThreadQuestion] = useState("");
  const [result, setResult] = useState<DebateResult | null>(null);
  const [messages, setMessages] = useState<DebateMessage[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<File[]>([]);

  const [sessions, setSessions] = useState<DebateSessionItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [debatersOpen, setDebatersOpen] = useState(false);

  // Load sessions on mount (and when login state changes)
  useEffect(() => {
    if (!isLoggedIn) return;
    fetch(`${API_BASE_URL}/api/sessions`, { headers: authHeaders() })
      .then(async (r) => {
        if (r.status === 401) {
          clearAuthSession();
          toast.info("Session expired. Please sign in again.");
          return [];
        }
        return r.ok ? r.json() : [];
      })
      .then((data) => {
        if (Array.isArray(data)) setSessions(data);
      })
      .catch(() => {});
  }, [isLoggedIn]);

  const canRun = useMemo(
    () => personas.length > 0 && composerText.trim().length > 0 && !isLoading,
    [personas.length, composerText, isLoading]
  );

  /** After first send (or restoring a session), composer docks to the bottom like ChatGPT. */
  const hasActiveDebate = useMemo(
    () => isLoading || result !== null || Boolean(error),
    [isLoading, result, error]
  );

  const handleAddPersona = (persona: Omit<Persona, "id">) => {
    setPersonas((prev) => {
      if (prev.length >= MAX_DEBATERS_PER_SESSION) {
        toast.info(`You can add up to ${MAX_DEBATERS_PER_SESSION} debaters per session.`);
        return prev;
      }
      return [...prev, { id: nanoid(), ...persona }];
    });
  };

  const handleRemovePersona = (id: string) => {
    setPersonas((prev) => prev.filter((p) => p.id !== id));
  };

  const handleUpdatePersona = (updated: Persona) => {
    setPersonas((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  const saveSession = useCallback(
    async (sessionId: string | null, q: string, ps: Persona[], r: DebateResult) => {
      if (!isLoggedIn) return null;
      const body = {
        title: sessionTitle(q),
        question: q,
        personas: ps.map(({ id, name, description, icon, personaBasis }) => ({
          id,
          name,
          description,
          icon,
          ...(personaBasis?.trim() ? { persona_basis: personaBasis.trim() } : {}),
        })),
        result: r,
      };
      if (sessionId) {
        const res = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify(body),
        });
        if (res.status === 401) {
          clearAuthSession();
          toast.info("Session expired. Please sign in again.");
          return null;
        }
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? { ...s, ...body, result: r as object, updated_at: new Date().toISOString() }
              : s
          )
        );
        return sessionId;
      } else {
        const res = await fetch(`${API_BASE_URL}/api/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify(body),
        });
        if (res.status === 401) {
          clearAuthSession();
          toast.info("Session expired. Please sign in again.");
          return null;
        }
        if (res.ok) {
          const created: DebateSessionItem = await res.json();
          setSessions((prev) => [created, ...prev]);
          return created.id;
        }
        return null;
      }
    },
    [isLoggedIn]
  );

  const handleRun = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const runQuestion = composerText.trim();
      // If logged in, ensure we have a session for message storage.
      let sid = currentSessionId;
      if (isLoggedIn && !sid) {
        const res = await fetch(`${API_BASE_URL}/api/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({
            title: sessionTitle(runQuestion),
            question: runQuestion,
            personas: personas.map(({ id, name, description, icon, personaBasis }) => ({
              id,
              name,
              description,
              icon,
              ...(personaBasis?.trim() ? { persona_basis: personaBasis.trim() } : {}),
            })),
          }),
        });
        if (res.ok) {
          const created: DebateSessionItem = await res.json();
          setSessions((prev) => [created, ...prev]);
          sid = created.id;
          setCurrentSessionId(created.id);
        }
      }

      const payload = {
        question: runQuestion,
        ...(sid ? { session_id: sid } : {}),
        num_rounds: 2,
        personas: personas.map((p) => ({
          id: p.id,
          name: p.name,
          description: p.description,
          ...(p.personaBasis?.trim() ? { persona_basis: p.personaBasis.trim() } : {}),
        })),
      };
      if (attachments.length > 0) {
        const totalBytes = attachments.reduce((sum, f) => sum + f.size, 0);
        if (totalBytes > 12 * 1024 * 1024) {
          throw new Error("Attachments too large (max 12MB total for demo).");
        }
        const encoded = await Promise.all(
          attachments.slice(0, 8).map(
            (file) =>
              new Promise<{ filename: string; mime_type: string; base64: string }>((resolve, reject) => {
                const reader = new FileReader();
                reader.onerror = () => reject(new Error(`Could not read attachment: ${file.name}`));
                reader.onload = () => {
                  const dataUrl = String(reader.result || "");
                  const comma = dataUrl.indexOf(",");
                  const base64 = comma >= 0 ? dataUrl.slice(comma + 1) : "";
                  resolve({
                    filename: file.name,
                    mime_type: file.type || "application/octet-stream",
                    base64,
                  });
                };
                reader.readAsDataURL(file);
              })
          )
        );
        (payload as any).attachments = encoded;
      }

      const response = await fetch(`${API_BASE_URL}/api/debate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(isLoggedIn ? authHeaders() : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errJson = (await response.json().catch(() => null)) as {
          detail?: unknown;
        } | null;
        const detail = errJson?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((d) => JSON.stringify(d)).join("; ")
              : `Request failed (${response.status})`;
        if (response.status === 429) {
          if (isLoggedIn) {
            toast.info(
              "Prototype limit reached: you can run up to 10 debates per day on a normal account. Try again tomorrow."
            );
          } else {
            toast.info(
              "Prototype limit reached: guest mode allows up to 5 debates per day. Sign in for 10/day, or try again tomorrow."
            );
          }
        }
        throw new Error(msg);
      }

      const raw: ApiDebateResponse = await response.json();
      const data: DebateResult = {
        judge: raw.judge,
        rounds: raw.rounds.map((r) => ({
          roundNumber: r.round_number,
          label: r.label,
          personaAnswers: r.persona_answers.map((a) => ({
            personaId: a.persona_id,
            personaName: a.persona_name,
            personaDescription: a.persona_description,
            answer: a.answer,
          })),
        })),
        topicRelevanceQa: mapCalibrationRows(raw.topic_relevance_qa),
        reasoningQualityQa: mapCalibrationRows(raw.reasoning_quality_qa),
      };

      setResult(data);
      setThreadQuestion(runQuestion);

      // Refresh message log for WhatsApp-style view (logged-in sessions).
      if (isLoggedIn && sid) {
        const msgRes = await fetch(`${API_BASE_URL}/api/sessions/${sid}/messages`, {
          headers: authHeaders(),
        });
        if (msgRes.ok) {
          const rawMsgs = (await msgRes.json().catch(() => null)) as any;
          if (Array.isArray(rawMsgs)) {
            setMessages(
              rawMsgs.map((m) => ({
                id: String(m.id),
                role: m.role,
                author: m.author ?? null,
                content: String(m.content ?? ""),
                roundNumber: m.round_number ?? null,
                roundLabel: m.round_label ?? null,
                personaId: m.persona_id ?? null,
                personaDescription: m.persona_description ?? null,
                createdAt: String(m.created_at ?? ""),
              }))
            );
          }
        }
      } else {
        // Not logged in: keep an in-memory chat log so each run appends below.
        const now = new Date().toISOString();
        const baseId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const runMsgs: DebateMessage[] = [];
        runMsgs.push({
          id: `${baseId}-q`,
          role: "user",
          author: "You",
          content: runQuestion,
          roundNumber: null,
          roundLabel: null,
          personaId: null,
          personaDescription: null,
          createdAt: now,
        });
        for (const round of data.rounds) {
          for (const a of round.personaAnswers) {
            runMsgs.push({
              id: `${baseId}-r${round.roundNumber}-${a.personaId}`,
              role: "persona",
              author: a.personaName,
              content: a.answer,
              roundNumber: round.roundNumber,
              roundLabel: round.label,
              personaId: a.personaId,
              personaDescription: a.personaDescription,
              createdAt: now,
            });
          }
        }
        runMsgs.push({
          id: `${baseId}-judge`,
          role: "judge",
          author: "Judge",
          content: `${data.judge.summary}\n\nReasoning:\n${data.judge.reasoning}`,
          roundNumber: null,
          roundLabel: null,
          personaId: null,
          personaDescription: null,
          createdAt: now,
        });
        setMessages((prev) => [...(prev ?? []), ...runMsgs]);
      }

      // Clear composer so a new question doesn't overwrite the last run.
      setComposerText("");
      setAttachments([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const loadMessages = useCallback(
    async (sid: string | null) => {
      if (!isLoggedIn || !sid) return;
      const res = await fetch(`${API_BASE_URL}/api/sessions/${sid}/messages`, {
        headers: authHeaders(),
      });
      if (!res.ok) {
        setMessages(null);
        return;
      }
      const rawMsgs = (await res.json().catch(() => null)) as any;
      if (!Array.isArray(rawMsgs)) {
        setMessages(null);
        return;
      }
      setMessages(
        rawMsgs.map((m) => ({
          id: String(m.id),
          role: m.role,
          author: m.author ?? null,
          content: String(m.content ?? ""),
          roundNumber: m.round_number ?? null,
          roundLabel: m.round_label ?? null,
          personaId: m.persona_id ?? null,
          personaDescription: m.persona_description ?? null,
          createdAt: String(m.created_at ?? ""),
        }))
      );
    },
    [isLoggedIn]
  );

  const handleSelectSession = (session: DebateSessionItem) => {
    setCurrentSessionId(session.id);
    // Switching chats should not prefill the composer, but should still display the session question.
    setComposerText("");
    setAttachments([]);
    setThreadQuestion(session.question || "");
    const raw = session.personas as Persona[];
    if (Array.isArray(raw) && raw.length > 0) {
      const mapped = raw.map((p) => ({
        id: typeof p.id === "string" ? p.id : nanoid(),
        name: typeof p.name === "string" ? p.name : "",
        description: typeof p.description === "string" ? p.description : "",
        icon: typeof p.icon === "string" ? p.icon : "User",
        personaBasis:
          typeof (p as { personaBasis?: unknown }).personaBasis === "string"
            ? (p as { personaBasis: string }).personaBasis
            : typeof (p as { persona_basis?: unknown }).persona_basis === "string"
              ? (p as { persona_basis: string }).persona_basis
              : undefined,
      }));
      if (mapped.length > MAX_DEBATERS_PER_SESSION) {
        toast.info(
          `This session had more than ${MAX_DEBATERS_PER_SESSION} debaters; only the first ${MAX_DEBATERS_PER_SESSION} were restored.`
        );
      }
      setPersonas(mapped.slice(0, MAX_DEBATERS_PER_SESSION));
    } else {
      setPersonas(DEFAULT_PERSONAS);
    }
    setResult(debateResultFromStored(session.result));
    void loadMessages(session.id);
    setError(null);
  };

  const handleNewSession = async () => {
    setCurrentSessionId(null);
    setComposerText("");
    setThreadQuestion("");
    setAttachments([]);
    setPersonas(DEFAULT_PERSONAS);
    setResult(null);
    setMessages(isLoggedIn ? null : []);
    setError(null);
  };

  const handleDeleteSession = async (id: string) => {
    if (!isLoggedIn) return;
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (currentSessionId === id) {
      setCurrentSessionId(null);
      setComposerText("");
      setThreadQuestion("");
      setPersonas(DEFAULT_PERSONAS);
      setResult(null);
    }
    fetch(`${API_BASE_URL}/api/sessions/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    }).catch(() => {});
  };

  return (
    <>
      <GradientBackground />
      <ThemedToastContainer position="top-center" autoClose={5000} />

      <div
        className={`relative z-10 flex h-[100dvh] min-h-0 max-h-[100dvh] overflow-hidden ${pageShell}`}
      >
        <SessionSidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          isLoggedIn={isLoggedIn}
          onSelect={handleSelectSession}
          onNew={handleNewSession}
          onDelete={handleDeleteSession}
        />

        <div className="relative z-10 flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <header
            className={`flex shrink-0 items-center justify-between gap-3 px-4 py-3 backdrop-blur-sm sm:px-6 ${stickyHeader}`}
          >
            <div className="min-w-0 flex-1" aria-hidden />
            <div className="shrink-0 text-center">
              <h1 className={`text-sm font-semibold tracking-tight sm:text-base ${formHeading}`}>
                Consensia
              </h1>
            </div>
            <div className="flex min-w-0 flex-1 justify-end">
              <DebateUserMenu isLoggedIn={isLoggedIn} />
            </div>
          </header>

          <main className="flex min-h-0 flex-1 flex-col">
            {!hasActiveDebate ? (
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-1 px-3 py-10 sm:px-4">
                  <DebateComposer
                    question={composerText}
                    onChange={setComposerText}
                    attachments={attachments}
                    onAttachmentsChange={setAttachments}
                    onRun={handleRun}
                    canRun={canRun}
                    isLoading={isLoading}
                  />
                  <DebatersBlock
                    debatersOpen={debatersOpen}
                    setDebatersOpen={setDebatersOpen}
                    isLoggedIn={isLoggedIn}
                    personas={personas}
                    maxDebaters={MAX_DEBATERS_PER_SESSION}
                    onAddPersona={handleAddPersona}
                    onRemovePersona={handleRemovePersona}
                    onUpdatePersona={handleUpdatePersona}
                    placement="below"
                  />
                </div>
              </div>
            ) : (
              <>
                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
                  <DebateChatThread
                    question={threadQuestion}
                    result={result}
                    messages={messages}
                    error={error}
                    isLoading={isLoading}
                    personaCount={personas.length}
                  />
                </div>
                <div className={debateDockStrip}>
                  <DebateComposer
                    question={composerText}
                    onChange={setComposerText}
                    attachments={attachments}
                    onAttachmentsChange={setAttachments}
                    onRun={handleRun}
                    canRun={canRun}
                    isLoading={isLoading}
                  />
                  <DebatersBlock
                    debatersOpen={debatersOpen}
                    setDebatersOpen={setDebatersOpen}
                    isLoggedIn={isLoggedIn}
                    personas={personas}
                    maxDebaters={MAX_DEBATERS_PER_SESSION}
                    onAddPersona={handleAddPersona}
                    onRemovePersona={handleRemovePersona}
                    onUpdatePersona={handleUpdatePersona}
                    placement="above"
                  />
                </div>
              </>
            )}
          </main>
        </div>
      </div>
    </>
  );
}
