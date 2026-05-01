export type Persona = {
  id: string;
  name: string;
  description: string;
  icon: string;
  /**
   * Optional raw material used to build this persona (CV text, researcher scrape, etc.).
   * Sent to the judge for topic-fit calibration; falls back to description only when empty.
   */
  personaBasis?: string;
};

/** Server-backed favorite persona (same shape as Persona except `id` is stable across debates). */
export type SavedFavoritePersona = {
  id: string;
  name: string;
  description: string;
  icon: string;
  created_at: string;
};

export type PersonaResponse = {
  personaId: string;
  personaName: string;
  personaDescription: string;
  answer: string;
};

export type JudgeConsensus = {
  summary: string;
  reasoning: string;
};

/** One row from judge QA (topic fit 0–9 or reasoning quality 0–9). */
export type PersonaCalibrationScore = {
  personaId: string;
  personaName: string;
  score: number;
  rationale: string;
};

export type DebateRound = {
  roundNumber: number;
  label: string;
  personaAnswers: PersonaResponse[];
};

export type DebateResult = {
  rounds: DebateRound[];
  topicRelevanceQa?: PersonaCalibrationScore[];
  reasoningQualityQa?: PersonaCalibrationScore[];
  judge: JudgeConsensus;
};

export type DebateMessage = {
  id: string;
  role: "user" | "persona" | "judge" | "system";
  author: string | null;
  content: string;
  roundNumber: number | null;
  roundLabel: string | null;
  personaId: string | null;
  personaDescription: string | null;
  createdAt: string;
};
