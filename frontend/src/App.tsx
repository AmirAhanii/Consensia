import { useMemo, useState } from "react";
import { API_BASE_URL } from "./config.ts";
import { JudgeConsensus, Persona, PersonaResponse } from "./types.ts";
import { nanoid } from "./utils/nanoid.ts";

type RunResponse = {
  personas: PersonaResponse[];
  judge: JudgeConsensus;
};

const DEFAULT_PERSONAS: Persona[] = [
  {
    id: nanoid(),
    name: "Junior Software Engineer",
    description: "1 year experience, recently graduated, focuses on quick solutions"
  },
  {
    id: nanoid(),
    name: "Senior Software Engineer",
    description: "10 years experience, prioritizes scalability and maintainability"
  }
];

function App() {
  const [personas, setPersonas] = useState<Persona[]>(DEFAULT_PERSONAS);
  const [newPersona, setNewPersona] = useState({ name: "", description: "" });
  const [question, setQuestion] = useState("");
  const [responses, setResponses] = useState<RunResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canRun = useMemo(() => {
    return personas.length > 0 && question.trim().length > 0 && !isLoading;
  }, [personas.length, question, isLoading]);

  const handleAddPersona = () => {
    if (!newPersona.name.trim() || !newPersona.description.trim()) {
      return;
    }

    const persona: Persona = {
      id: nanoid(),
      name: newPersona.name.trim(),
      description: newPersona.description.trim()
    };

    setPersonas((prev) => [...prev, persona]);
    setNewPersona({ name: "", description: "" });
  };

  const handleRemovePersona = (id: string) => {
    setPersonas((prev) => prev.filter((persona) => persona.id !== id));
  };

  const handleRun = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const payload = {
        question,
        personas: personas.map(({ id, name, description }) => ({
          id,
          name,
          description
        }))
      };

      const response = await fetch(`${API_BASE_URL}/api/consensus`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const data = (await response.json()) as RunResponse;
      setResponses(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setResponses(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-col gap-2 px-6 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Consensia</h1>
            <p className="text-sm text-slate-400">
              Prototype multi-persona debate with an LLM judge.
            </p>
          </div>
          <button
            className="inline-flex items-center justify-center rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={handleRun}
            disabled={!canRun}
          >
            {isLoading ? "Running…" : "Run Debate"}
          </button>
        </div>
      </header>

      <main className="mx-auto grid max-w-5xl gap-8 px-6 py-10 lg:grid-cols-[360px_1fr]">
        <section className="space-y-6">
          <article className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-950/40">
            <h2 className="text-lg font-semibold">Personas</h2>
            <p className="mt-1 text-sm text-slate-400">
              Define the experts who will answer the question.
            </p>

            <div className="mt-4 space-y-4">
              {personas.map((persona) => (
                <div
                  key={persona.id}
                  className="rounded-lg border border-slate-800 bg-slate-900/80 p-4"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100">
                        {persona.name}
                      </h3>
                      <p className="mt-1 text-xs text-slate-400">
                        {persona.description}
                      </p>
                    </div>
                    <button
                      onClick={() => handleRemovePersona(persona.id)}
                      className="text-xs text-slate-400 transition hover:text-rose-400"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 space-y-3 border-t border-slate-800 pt-4">
              <h3 className="text-sm font-semibold text-slate-200">Add Persona</h3>
              <input
                className="w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                placeholder="Persona name"
                value={newPersona.name}
                onChange={(event) =>
                  setNewPersona((prev) => ({ ...prev, name: event.target.value }))
                }
              />
              <textarea
                className="h-20 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                placeholder="Persona background and traits"
                value={newPersona.description}
                onChange={(event) =>
                  setNewPersona((prev) => ({
                    ...prev,
                    description: event.target.value
                  }))
                }
              />
              <button
                className="w-full rounded-md border border-indigo-500/40 bg-indigo-500/10 px-3 py-2 text-sm font-medium text-indigo-200 transition hover:bg-indigo-500/20"
                onClick={handleAddPersona}
              >
                Add Persona
              </button>
            </div>
          </article>

          <article className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-950/40">
            <h2 className="text-lg font-semibold">Question</h2>
            <textarea
              className="mt-3 min-h-[160px] w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              placeholder="What would you like the personas to discuss?"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </article>
        </section>

        <section className="space-y-6">
          <article className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-950/40">
            <h2 className="text-lg font-semibold">Results</h2>
            {error ? (
              <p className="mt-3 text-sm text-rose-400">{error}</p>
            ) : (
              <p className="mt-1 text-sm text-slate-400">
                {responses
                  ? "View each persona response and the judge consensus."
                  : "Run a debate to see persona outputs and the judge consensus."}
              </p>
            )}

            {responses && (
              <div className="mt-5 space-y-5">
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
                    Persona Answers
                  </h3>
                  {responses.personas.map((resp) => (
                    <div
                      key={resp.personaId}
                      className="rounded-lg border border-slate-800 bg-slate-950/60 p-4"
                    >
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-300">
                          {resp.personaName}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                          {resp.personaDescription}
                        </p>
                      </div>
                      <p className="mt-3 whitespace-pre-wrap text-sm text-slate-100">
                        {resp.answer}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
                    Judge Consensus
                  </h3>
                  <div className="rounded-lg border border-indigo-500/40 bg-indigo-500/5 p-4">
                    <p className="text-sm font-semibold text-indigo-200">
                      Summary
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-slate-100">
                      {responses.judge.summary}
                    </p>
                    <p className="mt-4 text-sm font-semibold text-indigo-200">
                      Reasoning
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-slate-100">
                      {responses.judge.reasoning}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </article>
        </section>
      </main>
    </div>
  );
}

export default App;

