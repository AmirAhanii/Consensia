import React from "react";

type HeaderProps = {
  onRun: () => void;
  canRun: boolean;
  isLoading: boolean;
  personaCount: number;
  questionLength: number;
};

export const Header: React.FC<HeaderProps> = ({
  onRun,
  canRun,
  isLoading,
  personaCount,
  questionLength
}) => {
  return (
    <header className="border-b border-purple-900/40 bg-black/60 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-purple-100">Consensia</h1>
          <p className="mt-1 text-sm text-purple-300/70">
            Coordinate AI personas with a judge synthesizing their consensus.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-full border border-purple-800/40 bg-black/50 px-4 py-2 text-xs uppercase tracking-wide text-purple-300/70">
            <span className="h-2 w-2 rounded-full bg-fuchsia-400 shadow-[0_0_8px_rgba(236,72,153,0.6)]" />
            <span>{personaCount} personas</span>
            <span className="text-purple-500/60">|</span>
            <span>{questionLength} chars</span>
          </div>
          <button
            className="relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-full bg-gradient-to-r from-purple-600 via-fuchsia-500 to-purple-600 px-6 py-2 text-sm font-semibold text-white shadow-lg shadow-purple-900/50 transition hover:shadow-fuchsia-500/40 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={onRun}
            disabled={!canRun}
          >
            <span className="absolute inset-0 opacity-0 transition hover:opacity-20" />
            {isLoading ? "Running…" : "Run Debate"}
          </button>
        </div>
      </div>
    </header>
  );
};

