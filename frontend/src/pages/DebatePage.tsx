import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { GradientBackground } from "../components/GradientBackground";
import { Header } from "../components/Header";
import { PersonaPanel } from "../components/PersonaPanel";
import { QuestionPanel } from "../components/QuestionPanel";
import { ResultsPanel } from "../components/ResultsPanel";
import { SessionSidebar, type DebateSessionItem } from "../components/SessionSidebar";
import { API_BASE_URL } from "../config";
import { DebateResult, Persona } from "../types";
import { nanoid } from "../utils/nanoid";
import { ToastContainer } from "react-toastify";

type ApiPersonaAnswer = {
  persona_id: string;
  persona_name: string;
  persona_description: string;
  answer: string;
};

type ApiDebateResponse = {
  rounds: {
    round_number: number;
    label: string;
    persona_answers: ApiPersonaAnswer[];
  }[];
  judge: { summary: string; reasoning: string };
};

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

function getToken(): string | null {
  return localStorage.getItem("consensia_access_token");
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function sessionTitle(question: string): string {
  const q = question.trim();
  return q.length > 60 ? q.slice(0, 60) + "…" : q || "New Debate";
}

export default function DebatePage() {
  const navigate = useNavigate();

  useEffect(() => {
    document.title = "Consensia App — Debate Workspace";
  }, []);

  const isLoggedIn = Boolean(getToken());

  const [personas, setPersonas] = useState<Persona[]>(DEFAULT_PERSONAS);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<DebateResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sessions, setSessions] = useState<DebateSessionItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Load sessions on mount
  useEffect(() => {
    if (!isLoggedIn) return;
    fetch(`${API_BASE_URL}/api/sessions`, { headers: authHeaders() })
      .then((r) => r.ok ? r.json() : [])
      .then((data) => { if (Array.isArray(data)) setSessions(data); })
      .catch(() => {});
  }, []);

  const canRun = useMemo(
    () => personas.length > 0 && question.trim().length > 0 && !isLoading,
    [personas.length, question, isLoading]
  );

  const handleAddPersona = (persona: Omit<Persona, "id">) => {
    setPersonas((prev) => [...prev, { id: nanoid(), ...persona }]);
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
        personas: ps.map(({ id, name, description, icon }) => ({ id, name, description, icon })),
        result: r,
      };
      if (sessionId) {
        await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify(body),
        });
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
      const payload = {
        question,
        num_rounds: 2,
        personas: personas.map(({ id, name, description }) => ({ id, name, description })),
      };

      const response = await fetch(`${API_BASE_URL}/api/debate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error(`Request failed: ${response.status}`);

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
      };

      setResult(data);

      const sid = await saveSession(currentSessionId, question, personas, data);
      if (sid && !currentSessionId) setCurrentSessionId(sid);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSession = (session: DebateSessionItem) => {
    setCurrentSessionId(session.id);
    setQuestion(session.question);
    setPersonas(
      (session.personas as Persona[]).length > 0
        ? (session.personas as Persona[])
        : DEFAULT_PERSONAS
    );
    setResult((session.result as DebateResult) ?? null);
    setError(null);
  };

  const handleNewSession = async () => {
    setCurrentSessionId(null);
    setQuestion("");
    setPersonas(DEFAULT_PERSONAS);
    setResult(null);
    setError(null);

    if (!isLoggedIn) return;
    const res = await fetch(`${API_BASE_URL}/api/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ title: "New Debate", question: "", personas: [] }),
    });
    if (res.ok) {
      const created: DebateSessionItem = await res.json();
      setSessions((prev) => [created, ...prev]);
      setCurrentSessionId(created.id);
    }
  };

  const handleDeleteSession = async (id: string) => {
    if (!isLoggedIn) return;
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (currentSessionId === id) {
      setCurrentSessionId(null);
      setQuestion("");
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
      <ToastContainer position="top-center" autoClose={5000} theme="dark" />

      <div className="relative z-10 flex min-h-screen text-purple-50">
        <SessionSidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          isLoggedIn={isLoggedIn}
          onSelect={handleSelectSession}
          onNew={handleNewSession}
          onDelete={handleDeleteSession}
        />

        <div className="flex-1 min-w-0">
          <div className="px-6 pt-6">
            <button
              type="button"
              onClick={() => navigate("/")}
              className="rounded-xl border border-purple-800/40 bg-black/40 px-4 py-2 text-sm text-purple-200 transition hover:border-purple-600 hover:text-white"
            >
              ← Back to Homepage
            </button>
          </div>

          <Header
            onRun={handleRun}
            canRun={canRun}
            isLoading={isLoading}
            personaCount={personas.length}
            questionLength={question.length}
          />

          <main className="px-6 py-10">
            <div className="grid gap-8 lg:grid-cols-[380px_1fr]">
              <div className="space-y-6">
                <QuestionPanel question={question} onChange={setQuestion} />
                <PersonaPanel
                  personas={personas}
                  onAddPersona={handleAddPersona}
                  onRemovePersona={handleRemovePersona}
                  onUpdatePersona={handleUpdatePersona}
                />
              </div>

              <ResultsPanel
                result={result}
                personaCount={personas.length}
                error={error}
                isLoading={isLoading}
              />
            </div>
          </main>
        </div>
      </div>
    </>
  );
}
