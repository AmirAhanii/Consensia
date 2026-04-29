export type Persona = {
  id: string;
  name: string;
  description: string;
  icon: string;
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

export type DebateRound = {
  roundNumber: number;
  label: string;
  personaAnswers: PersonaResponse[];
};

export type DebateResult = {
  rounds: DebateRound[];
  judge: JudgeConsensus;
};

