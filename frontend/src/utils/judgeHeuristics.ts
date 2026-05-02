import type { DebateResult } from "../types";

export type JudgeHeuristics = {
  hasData: boolean;
  /** Mean combined calibration (topic + reasoning where present), scaled to 0–100 vs max 9. */
  calibrationConfidencePct: number | null;
  /** Personas within 1 point of the best combined calibration score. */
  agreementSupportCount: number | null;
  agreementTotal: number | null;
  footnote: string;
};

/**
 * Heuristic metrics from judge QA tables — useful for demos, not a statistical confidence interval.
 */
export function computeJudgeHeuristics(result: DebateResult): JudgeHeuristics {
  const topic = result.topicRelevanceQa ?? [];
  const reason = result.reasoningQualityQa ?? [];
  if (topic.length === 0 && reason.length === 0) {
    return {
      hasData: false,
      calibrationConfidencePct: null,
      agreementSupportCount: null,
      agreementTotal: null,
      footnote:
        "No topic/reasoning calibration table was returned for this run, so alignment metrics are unavailable.",
    };
  }

  const byId = new Map<
    string,
    { name: string; topic?: number; reason?: number }
  >();

  for (const r of topic) {
    const cur = byId.get(r.personaId) ?? { name: r.personaName };
    cur.topic = r.score;
    byId.set(r.personaId, cur);
  }
  for (const r of reason) {
    const cur = byId.get(r.personaId) ?? { name: r.personaName };
    cur.reason = r.score;
    byId.set(r.personaId, cur);
  }

  const combined: { id: string; name: string; value: number }[] = [];
  for (const [id, row] of byId) {
    const parts = [row.topic, row.reason].filter((x): x is number => typeof x === "number");
    if (parts.length === 0) continue;
    const value = parts.reduce((a, b) => a + b, 0) / parts.length;
    combined.push({ id, name: row.name, value });
  }

  if (combined.length === 0) {
    return {
      hasData: false,
      calibrationConfidencePct: null,
      agreementSupportCount: null,
      agreementTotal: null,
      footnote: "Calibration rows were empty.",
    };
  }

  const maxV = Math.max(...combined.map((c) => c.value));
  const threshold = maxV - 1;
  const supporting = combined.filter((c) => c.value >= threshold).length;
  const mean = combined.reduce((s, c) => s + c.value, 0) / combined.length;
  const calibrationConfidencePct = Math.min(100, Math.max(0, Math.round((mean / 9) * 100)));

  return {
    hasData: true,
    calibrationConfidencePct,
    agreementSupportCount: supporting,
    agreementTotal: combined.length,
    footnote:
      "Alignment counts personas within 1 point of the strongest average (topic + reasoning) calibration. " +
      "Confidence scales the mean of those averages to a 0–100 display vs a 9-point scale — heuristic only.",
  };
}
