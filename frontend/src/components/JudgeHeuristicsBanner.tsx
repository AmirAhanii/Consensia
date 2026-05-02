import React, { useMemo } from "react";
import type { DebateResult } from "../types";
import { computeJudgeHeuristics } from "../utils/judgeHeuristics";

type Props = {
  result: DebateResult;
};

export const JudgeHeuristicsBanner: React.FC<Props> = ({ result }) => {
  const h = useMemo(() => computeJudgeHeuristics(result), [result]);

  if (!h.hasData) {
    return (
      <div className="mx-auto mb-3 max-w-[95%] rounded-xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-inline)] px-3 py-2 text-[11px] leading-snug text-[var(--c-fg-muted)]">
        {h.footnote}
      </div>
    );
  }

  return (
    <div className="mx-auto mb-3 max-w-[95%] rounded-xl border border-fuchsia-500/35 bg-fuchsia-950/25 px-3 py-2.5 light:border-fuchsia-400/40 light:bg-fuchsia-100/60">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-fuchsia-300 light:text-fuchsia-800">
        Heuristic signals
      </p>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-purple-100 light:text-violet-950">
        <span>
          <span className="text-[var(--c-fg-hint)]">Calibration confidence: </span>
          <span className="font-semibold tabular-nums">{h.calibrationConfidencePct}%</span>
        </span>
        <span>
          <span className="text-[var(--c-fg-hint)]">Agent alignment: </span>
          <span className="font-semibold tabular-nums">
            {h.agreementSupportCount} / {h.agreementTotal}
          </span>
          <span className="text-[var(--c-fg-hint)]"> within 1 pt of strongest</span>
        </span>
      </div>
      <p className="mt-1.5 text-[10px] leading-snug text-purple-300/85 light:text-violet-800/90">{h.footnote}</p>
    </div>
  );
};
