import type {
  DebateResult,
  DebateRound,
  JudgeConsensus,
  PersonaCalibrationScore,
  PersonaResponse,
} from "../types";

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function normPersonaAnswer(a: Record<string, unknown>): PersonaResponse {
  return {
    personaId: String(a.personaId ?? a.persona_id ?? ""),
    personaName: String(a.personaName ?? a.persona_name ?? ""),
    personaDescription: String(a.personaDescription ?? a.persona_description ?? ""),
    answer: String(a.answer ?? ""),
  };
}

function normRound(r: Record<string, unknown>): DebateRound | null {
  const roundNumber =
    typeof r.roundNumber === "number"
      ? r.roundNumber
      : typeof r.round_number === "number"
        ? r.round_number
        : null;
  const label = typeof r.label === "string" ? r.label : "";
  const pa = r.personaAnswers ?? r.persona_answers;
  if (roundNumber === null || !Array.isArray(pa)) return null;
  const personaAnswers = pa
    .filter(isRecord)
    .map(normPersonaAnswer)
    .filter((p) => p.personaId || p.personaName || p.answer);
  return { roundNumber, label, personaAnswers };
}

function normQaRow(r: Record<string, unknown>): PersonaCalibrationScore {
  const scoreRaw = r.score;
  const score =
    typeof scoreRaw === "number" && Number.isFinite(scoreRaw)
      ? scoreRaw
      : Number(scoreRaw);
  return {
    personaId: String(r.personaId ?? r.persona_id ?? ""),
    personaName: String(r.personaName ?? r.persona_name ?? ""),
    score: Number.isFinite(score) ? score : 0,
    rationale: String(r.rationale ?? ""),
  };
}

function normQaList(raw: unknown): PersonaCalibrationScore[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter(isRecord).map(normQaRow);
}

/**
 * Sessions store `result` as JSON from the API (snake_case) or from the
 * browser (camelCase). Normalize to the frontend `DebateResult` shape.
 */
export function debateResultFromStored(raw: unknown): DebateResult | null {
  if (!isRecord(raw)) return null;

  const roundsRaw = Array.isArray(raw.rounds) ? raw.rounds : [];
  const rounds: DebateRound[] = [];
  for (const item of roundsRaw) {
    if (!isRecord(item)) continue;
    const round = normRound(item);
    if (round) rounds.push(round);
  }

  const judgeRaw = raw.judge;
  if (!isRecord(judgeRaw)) return null;
  const judge: JudgeConsensus = {
    summary: String(judgeRaw.summary ?? ""),
    reasoning: String(judgeRaw.reasoning ?? ""),
  };

  const hasJudgeText = Boolean(judge.summary?.trim() || judge.reasoning?.trim());
  if (rounds.length === 0 && !hasJudgeText) {
    return null;
  }

  return {
    rounds,
    topicRelevanceQa: normQaList(raw.topicRelevanceQa ?? raw.topic_relevance_qa),
    reasoningQualityQa: normQaList(raw.reasoningQualityQa ?? raw.reasoning_quality_qa),
    judge,
  };
}
