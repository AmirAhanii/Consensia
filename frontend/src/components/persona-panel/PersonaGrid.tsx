// src/components/persona-panel/PersonaGrid.tsx
import React from "react";
import { Persona } from "../../types";

type PersonaGridProps = {
  personas: Persona[];
  onSelectPersona: (persona: Persona) => void;
  renderIcon: (key: string, className?: string) => JSX.Element;
};

export const PersonaGrid: React.FC<PersonaGridProps> = ({
  personas,
  onSelectPersona,
  renderIcon,
}) => {
  return (
    <div className="mt-5 grid grid-cols-4 gap-4">
      {personas.map((persona) => (
        <button
          key={persona.id}
          onClick={() => onSelectPersona(persona)}
          className="group rounded-xl border border-purple-900/50 bg-black/40 hover:bg-purple-900/30 p-4 text-center transition shadow-md"
        >
          {renderIcon(persona.icon)}
        </button>
      ))}
    </div>
  );
};
