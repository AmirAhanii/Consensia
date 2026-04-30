import React from "react";
import { DebateResult, PersonaCalibrationScore } from "../types";

function QaTable({ title, rows }: { title: string; rows: PersonaCalibrationScore[] }) {
  if (!rows.length) return null;
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-purple-300 light:text-violet-700">
        {title}
      </h3>
      <div className="overflow-hidden rounded-xl border border-purple-800/40 bg-black/35 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-inline)]">
        <table className="w-full text-left text-xs text-purple-100 light:text-[var(--c-fg)]">
          <thead>
            <tr className="border-b border-purple-800/50 bg-purple-950/40 text-[10px] uppercase tracking-wide text-purple-400 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-hint)] light:text-violet-700">
              <th className="px-3 py-2 font-semibold">Persona</th>
              <th className="w-12 px-2 py-2 text-center font-semibold">0–9</th>
              <th className="px-3 py-2 font-semibold">Note</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.personaId}
                className="border-b border-purple-900/30 last:border-0 light:border-violet-200/40"
              >
                <td className="px-3 py-2 font-medium text-fuchsia-200/95 light:text-violet-800">
                  {row.personaName}
                </td>
                <td className="px-2 py-2 text-center tabular-nums font-semibold text-purple-50 light:text-[var(--c-fg)]">
                  {row.score}
                </td>
                <td className="px-3 py-2 text-purple-300/90 light:text-violet-700/90">{row.rationale}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

type ResultsPanelProps = {
  result: DebateResult | null;
  personaCount: number;
  error: string | null;
  isLoading: boolean;
};

export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  result,
  personaCount,
  error,
  isLoading,
}) => {
  const hasMultiplePersonas = personaCount > 1;
  const hasRounds = result && result.rounds.length > 0;
  const showMultipleRounds = result && result.rounds.length > 1;

  return (
    <article className="rounded-3xl border border-purple-900/40 bg-black/60 p-6 shadow-xl shadow-purple-950/30 backdrop-blur">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-purple-100">Results</h2>
        {isLoading && (
          <span className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-fuchsia-200">
            <span className="h-2 w-2 animate-pulse rounded-full bg-fuchsia-400" />
            Generating…
          </span>
        )}
      </div>

      {error ? (
        <p className="mt-4 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-100">
          {error}
        </p>
      ) : (
        <p className="mt-1 text-sm text-purple-300/70">
          {hasRounds && hasMultiplePersonas
            ? "Each round shows how personas responded and refined their positions."
            : hasRounds
              ? "One viewpoint below. Add another persona for a multi-round debate."
              : "Run a debate to see how personas argue and reach consensus."}
        </p>
      )}

      {hasRounds && (
        <div className="mt-6 space-y-8">
          {result.rounds.map((round, roundIdx) => (
            <section key={round.roundNumber} className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-purple-800/60 text-xs font-bold text-purple-200">
                  {round.roundNumber}
                </span>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-purple-200">
                  {showMultipleRounds ? `Round ${round.roundNumber} — ${round.label}` : round.label}
                </h3>
                {roundIdx > 0 && (
                  <span className="rounded-full border border-fuchsia-700/40 bg-fuchsia-900/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-fuchsia-300">
                    Rebuttal
                  </span>
                )}
              </div>

              <div className="grid gap-4">
                {round.personaAnswers.map((persona) => (
                  <div
                    key={persona.personaId}
                    className="group relative overflow-hidden rounded-2xl border border-purple-900/40 bg-gradient-to-br from-purple-950/50 to-black/60 p-4 shadow-inner shadow-black/40"
                  >
                    <div className="absolute inset-0 opacity-0 transition group-hover:opacity-100">
                      <div className="h-full w-full bg-[radial-gradient(circle_at_top_left,rgba(168,85,247,0.18),transparent_60%)]" />
                    </div>
                    <div className="relative flex flex-col gap-2">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wide text-fuchsia-300">
                          {persona.personaName}
                        </p>
                        <span className="rounded-full border border-purple-800/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-purple-300/70">
                          {roundIdx === 0 ? "Initial" : "Rebuttal"}
                        </span>
                      </div>
                      <p className="text-xs text-purple-300/70">{persona.personaDescription}</p>
                      <p className="whitespace-pre-wrap text-sm text-purple-100">{persona.answer}</p>
                    </div>
                  </div>
                ))}
              </div>

              {roundIdx < result.rounds.length - 1 && (
                <div className="flex items-center gap-3 pt-2">
                  <div className="h-px flex-1 bg-purple-900/40" />
                  <span className="text-[10px] uppercase tracking-widest text-purple-500">↓ rebuttals</span>
                  <div className="h-px flex-1 bg-purple-900/40" />
                </div>
              )}
            </section>
          ))}

          {result.topicRelevanceQa && result.topicRelevanceQa.length > 0 && (
            <QaTable title="Topic relevance (0–9, before debate)" rows={result.topicRelevanceQa} />
          )}
          {result.reasoningQualityQa && result.reasoningQualityQa.length > 0 && (
            <QaTable title="Reasoning quality (0–9, after debate)" rows={result.reasoningQualityQa} />
          )}

          {result.judge && hasMultiplePersonas && (
            <section className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="h-px flex-1 bg-fuchsia-900/40" />
                <span className="text-[10px] uppercase tracking-widest text-fuchsia-500">consensus</span>
                <div className="h-px flex-1 bg-fuchsia-900/40" />
              </div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-purple-200">Judge Consensus</h3>
              <div className="overflow-hidden rounded-2xl border border-fuchsia-500/30 bg-gradient-to-br from-fuchsia-900/60 to-black/70 p-5 shadow-lg shadow-purple-900/40">
                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-fuchsia-200">
                  <span className="h-2 w-2 rounded-full bg-fuchsia-400 shadow-[0_0_12px_rgba(236,72,153,0.7)]" />
                  Consensus summary
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm text-purple-100">{result.judge.summary}</p>
                <div className="mt-4 rounded-xl border border-fuchsia-500/30 bg-black/40 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-fuchsia-200">Reasoning</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-purple-100">
                    {result.judge.reasoning}
                  </p>
                </div>
              </div>
            </section>
          )}
        </div>
      )}
    </article>
  );
};
