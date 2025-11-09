import React, { useMemo, useState } from "react";
import { GradientBackground } from "./components/GradientBackground";
import { Header } from "./components/Header";
import { PersonaPanel } from "./components/PersonaPanel";
import { QuestionPanel } from "./components/QuestionPanel";
import { ResultsPanel } from "./components/ResultsPanel";
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
  const [question, setQuestion] = useState("");
  const [responses, setResponses] = useState<RunResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canRun = useMemo(() => personas.length > 0 && question.trim().length > 0 && !isLoading, [
    personas.length,
    question,
    isLoading
  ]);

  const handleAddPersona = (persona: Omit<Persona, "id">) => {
    const entry: Persona = {
      id: nanoid(),
      name: persona.name,
      description: persona.description
    };
    setPersonas((prev) => [...prev, entry]);
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

  const personaAnswers = responses?.personas ?? [];
  const judgeConsensus = responses?.judge ?? null;

  return (
    <>
      <GradientBackground />
      <div className="relative z-10 min-h-screen text-purple-50">
        <Header
          onRun={handleRun}
          canRun={canRun}
          isLoading={isLoading}
          personaCount={personas.length}
          questionLength={question.length}
        />

        <main className="mx-auto max-w-6xl px-6 py-10">
          <div className="grid gap-8 lg:grid-cols-[380px_1fr]">
            <div className="space-y-6">
              <PersonaPanel personas={personas} onAddPersona={handleAddPersona} onRemovePersona={handleRemovePersona} />
              <QuestionPanel question={question} onChange={setQuestion} />
            </div>
            <ResultsPanel personas={personaAnswers} judge={judgeConsensus} error={error} isLoading={isLoading} />
          </div>
        </main>
      </div>
    </>
  );
}

export default App;

