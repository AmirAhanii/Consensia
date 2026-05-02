import React, { useEffect, useRef } from "react";
import { DebateExportBar } from "./DebateExportBar";
import { JudgeHeuristicsBanner } from "./JudgeHeuristicsBanner";
import { DebateMessage, DebateResult, Persona } from "../types";
import type { DebateExportAttachmentMeta } from "../utils/debateExport";

function localUserLabel(): string | null {
  try {
    const name = localStorage.getItem("consensia_user_name");
    if (name && name.trim()) return name.trim();
    const email = localStorage.getItem("consensia_user_email");
    return email && email.trim() ? email.trim() : null;
  } catch {
    return null;
  }
}

type Props = {
  question: string;
  result: DebateResult | null;
  messages?: DebateMessage[] | null;
  error: string | null;
  isLoading: boolean;
  personaCount: number;
  personas: Persona[];
  attachmentMetaForExport: DebateExportAttachmentMeta[];
};

const AUTHOR_STYLES = [
  "border-violet-500/35 bg-violet-950/70 text-violet-50 light:border-violet-400/50 light:bg-violet-200/95 light:text-violet-950",
  "border-sky-500/35 bg-sky-950/70 text-sky-50 light:border-sky-400/45 light:bg-sky-100/95 light:text-sky-950",
  "border-emerald-500/35 bg-emerald-950/70 text-emerald-50 light:border-emerald-400/45 light:bg-emerald-100/95 light:text-emerald-950",
  "border-amber-500/35 bg-amber-950/80 text-amber-50 light:border-amber-400/45 light:bg-amber-100/95 light:text-amber-950",
  "border-rose-500/35 bg-rose-950/70 text-rose-50 light:border-rose-400/45 light:bg-rose-100/95 light:text-rose-950",
  "border-cyan-500/35 bg-cyan-950/70 text-cyan-50 light:border-cyan-400/45 light:bg-cyan-100/95 light:text-cyan-950",
];

function bubbleStyleForAuthor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return AUTHOR_STYLES[h % AUTHOR_STYLES.length];
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export const DebateChatThread: React.FC<Props> = ({
  question,
  result,
  messages,
  error,
  isLoading,
  personaCount,
  personas,
  attachmentMetaForExport,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevRef = useRef({ loading: isLoading, rounds: 0, msgLen: 0 });

  // Pin to bottom when a run finishes or new rounds appear — not on every question keystroke
  // (that prevented scrolling up to read earlier messages).
  useEffect(() => {
    const roundsLen = result?.rounds?.length ?? 0;
    const msgLen = messages?.length ?? 0;
    const loadingEnded = prevRef.current.loading && !isLoading;
    const roundsGrew = roundsLen > prevRef.current.rounds;
    const messagesGrew = msgLen > prevRef.current.msgLen;
    prevRef.current = { loading: isLoading, rounds: roundsLen, msgLen };

    if (loadingEnded || roundsGrew || messagesGrew) {
      const defer =
        typeof queueMicrotask === "function"
          ? queueMicrotask
          : (fn: () => void) => window.setTimeout(fn, 0);
      defer(() => bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }));
    }
  }, [isLoading, result, messages]);

  const showUserBubble =
    question.trim().length > 0 &&
    (Boolean(result) || isLoading || Boolean(error));
  const fallbackRounds = result?.rounds ?? [];
  const hasThread = Boolean(fallbackRounds.length);
  const safeMessages = Array.isArray(messages) ? messages : [];
  const hasDbThread = safeMessages.length > 0;
  const showGuestJudgeBlock =
    !hasDbThread &&
    Boolean(result && fallbackRounds.length > 0 && personaCount > 1 && result.judge);
  const showHeuristicsFooter =
    Boolean(result && !isLoading && fallbackRounds.length > 0) &&
    (hasDbThread || !showGuestJudgeBlock);

  return (
    <div className="mx-auto w-full max-w-3xl px-3 py-6 sm:px-4">
      {!showUserBubble && !hasThread && !error && !isLoading && (
        <div className="flex min-h-[40vh] flex-col items-center justify-center text-center">
          <p className="text-sm font-medium text-purple-200/90 light:text-violet-800">
            Start a debate
          </p>
          <p className="mt-2 max-w-md text-xs leading-relaxed text-purple-400/80 light:text-violet-600">
            Add debaters, ask your question, then run. Replies show below.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {error && (
          <div className="mx-auto max-w-lg rounded-2xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-center text-sm text-rose-100 light:border-rose-400/50 light:bg-rose-100/80 light:text-rose-900">
            {error}
          </div>
        )}

        {result && result.rounds.length > 0 && !isLoading && (
          <DebateExportBar
            question={question}
            personas={personas}
            attachments={attachmentMetaForExport}
            result={result}
            messages={messages}
          />
        )}

        {/* DB-backed thread (WhatsApp style): render full message log when available */}
        {hasDbThread &&
          (() => {
            const nodes: React.ReactNode[] = [];
            let lastRound: number | null = null;
            let inRun = false;

            for (const m of safeMessages) {
              if (m.role === "user") {
                inRun = true;
                lastRound = null;
                nodes.push(
                  <div key={m.id} className="flex justify-end">
                    <div className="max-w-[88%] rounded-2xl rounded-br-md border border-fuchsia-500/30 bg-gradient-to-br from-fuchsia-600/90 to-purple-700/90 px-4 py-3 text-sm text-white shadow-lg shadow-purple-950/40 light:from-fuchsia-500 light:to-violet-600 light:shadow-violet-300/40">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-fuchsia-100/80 light:text-fuchsia-900/90">
                        {m.author || localUserLabel() || "You"}
                      </p>
                      <p className="mt-1.5 whitespace-pre-wrap leading-relaxed">{m.content}</p>
                    </div>
                  </div>
                );
                continue;
              }

              if (m.role === "persona") {
                const rn = typeof m.roundNumber === "number" ? m.roundNumber : null;
                if (inRun && rn !== null && rn !== lastRound) {
                  lastRound = rn;
                  nodes.push(
                    <div key={`${m.id}-round`} className="flex items-center gap-3 py-2">
                      <div className="h-px flex-1 bg-purple-900/50 light:bg-violet-300/70" />
                      <span className="shrink-0 text-[10px] font-semibold uppercase tracking-widest text-purple-500 light:text-violet-600">
                        Round {rn}
                      </span>
                      <div className="h-px flex-1 bg-purple-900/50 light:bg-violet-300/70" />
                    </div>
                  );
                }

                const author = m.author || "Persona";
                nodes.push(
                  <div key={m.id} className="flex justify-start">
                    <div
                      className={`flex max-w-[88%] gap-2.5 rounded-2xl rounded-bl-md border px-3.5 py-3 shadow-md ${bubbleStyleForAuthor(
                        author
                      )}`}
                    >
                      <div
                        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-black/30 text-[11px] font-bold text-white/90 light:border-violet-400/50 light:bg-violet-300/60 light:text-violet-950"
                        aria-hidden
                      >
                        {initials(author)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[11px] font-semibold text-white/90 light:text-violet-950">
                          {author}
                        </p>
                        {m.personaDescription ? (
                          <p className="mt-0.5 line-clamp-2 text-[10px] leading-snug text-white/55 light:text-violet-800/85">
                            {m.personaDescription}
                          </p>
                        ) : null}
                        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-white/95 light:text-violet-950">
                          {m.content}
                        </p>
                      </div>
                    </div>
                  </div>
                );
                continue;
              }

              if (m.role === "judge") {
                inRun = false;
                lastRound = null;
                nodes.push(
                  <div key={m.id} className="mt-2 flex justify-center">
                    <div className="w-full max-w-[95%] rounded-2xl border border-fuchsia-500/35 bg-gradient-to-b from-fuchsia-950/50 to-black/60 p-4 shadow-xl shadow-purple-950/30 light:border-fuchsia-400/45 light:from-[var(--c-judge-from)] light:to-[var(--c-judge-to)] light:shadow-[color:var(--c-shadow-card)]">
                      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-fuchsia-300/90 light:text-fuchsia-800">
                        <span className="h-2 w-2 rounded-full bg-fuchsia-400" />
                        Judge
                      </div>
                      <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-purple-50 light:text-[var(--c-fg)]">
                        {m.content}
                      </p>
                    </div>
                  </div>
                );
                continue;
              }

              // system/unknown
              nodes.push(
                <div key={m.id} className="flex justify-center">
                  <div className="max-w-[95%] rounded-2xl border border-[color:var(--c-border-soft)] bg-black/20 px-4 py-2 text-xs text-[var(--c-fg-hint)] light:bg-[var(--c-surface-inline)]">
                    {m.content}
                  </div>
                </div>
              );
            }
            return nodes;
          })()}

        {/* Fallback (non-logged-in): old single-run rendering */}
        {!hasDbThread && showUserBubble && (
          <div className="flex justify-end">
            <div
              className="max-w-[88%] rounded-2xl rounded-br-md border border-fuchsia-500/30 bg-gradient-to-br from-fuchsia-600/90 to-purple-700/90 px-4 py-3 text-sm text-white shadow-lg shadow-purple-950/40 light:from-fuchsia-500 light:to-violet-600 light:shadow-violet-300/40"
              role="status"
            >
              <p className="text-[10px] font-semibold uppercase tracking-wider text-fuchsia-100/80 light:text-fuchsia-900/90">
                {localUserLabel() || "You"}
              </p>
              <p className="mt-1.5 whitespace-pre-wrap leading-relaxed">
                {question.trim()}
              </p>
            </div>
          </div>
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="max-w-[88%] rounded-2xl rounded-bl-md border border-[color:var(--c-border-soft)] bg-[var(--c-loading-bubble)] px-4 py-3 text-sm text-purple-200/90 light:border-[color:var(--c-border-strong)] light:text-[var(--c-fg)]">
              <div className="flex items-center gap-2">
                <span className="flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-fuchsia-400 [animation-delay:-0.2s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-fuchsia-400 [animation-delay:-0.1s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-fuchsia-400" />
                </span>
                <span className="text-xs text-[var(--c-fg-hint)]">
                  Debating…
                </span>
              </div>
            </div>
          </div>
        )}

        {!hasDbThread &&
          fallbackRounds.map((round, roundIdx) => (
          <React.Fragment key={round.roundNumber}>
            {roundIdx > 0 && (
              <div className="flex items-center gap-3 py-2">
                <div className="h-px flex-1 bg-purple-900/50 light:bg-violet-300/70" />
                <span className="shrink-0 text-[10px] font-semibold uppercase tracking-widest text-purple-500 light:text-violet-600">
                  Round {round.roundNumber}
                </span>
                <div className="h-px flex-1 bg-purple-900/50 light:bg-violet-300/70" />
              </div>
            )}
            {roundIdx === 0 && fallbackRounds.length > 1 && (
              <div className="flex justify-center py-1">
                <span className="rounded-full border border-[color:var(--c-border-soft)] bg-purple-950/50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-purple-300/90 light:border-[color:var(--c-border-strong)] light:bg-[var(--c-surface-chip)] light:text-[var(--c-fg)]">
                  {round.label}
                </span>
              </div>
            )}

            {(round.personaAnswers ?? []).map((persona) => (
              <div key={`${round.roundNumber}-${persona.personaId}`} className="flex justify-start">
                <div
                  className={`flex max-w-[88%] gap-2.5 rounded-2xl rounded-bl-md border px-3.5 py-3 shadow-md ${bubbleStyleForAuthor(
                    persona.personaName
                  )}`}
                >
                  <div
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-black/30 text-[11px] font-bold text-white/90 light:border-violet-400/50 light:bg-violet-300/60 light:text-violet-950"
                    aria-hidden
                  >
                    {initials(persona.personaName)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-semibold text-white/90 light:text-violet-950">
                      {persona.personaName}
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-[10px] leading-snug text-white/55 light:text-violet-800/85">
                      {persona.personaDescription}
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-white/95 light:text-violet-950">
                      {persona.answer}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </React.Fragment>
        ))}

        {showGuestJudgeBlock && result ? (
          <>
            <JudgeHeuristicsBanner result={result} />
            <div className="mt-1 flex justify-center">
              <div className="w-full max-w-[95%] rounded-2xl border border-fuchsia-500/35 bg-gradient-to-b from-fuchsia-950/50 to-black/60 p-4 shadow-xl shadow-purple-950/30 light:border-fuchsia-400/45 light:from-[var(--c-judge-from)] light:to-[var(--c-judge-to)] light:shadow-[color:var(--c-shadow-card)]">
                <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-fuchsia-300/90 light:text-fuchsia-800">
                  <span className="h-2 w-2 rounded-full bg-fuchsia-400" />
                  Judge consensus
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-purple-50 light:text-[var(--c-fg)]">
                  {result.judge.summary}
                </p>
                <details className="mt-3 rounded-xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-inline)] px-3 py-2 light:border-[color:var(--c-border)]">
                  <summary className="cursor-pointer text-xs font-medium text-purple-300/90 light:text-[var(--c-fg-muted)]">
                    Reasoning
                  </summary>
                  <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-purple-200/90 light:text-[var(--c-fg-muted)]">
                    {result.judge.reasoning}
                  </p>
                </details>
              </div>
            </div>
          </>
        ) : null}

        {showHeuristicsFooter && result ? <JudgeHeuristicsBanner result={result} /> : null}

        <div ref={bottomRef} className="h-2 shrink-0" aria-hidden />
      </div>
    </div>
  );
};
