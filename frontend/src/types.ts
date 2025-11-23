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

