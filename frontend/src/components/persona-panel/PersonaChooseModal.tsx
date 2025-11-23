// src/components/persona-panel/PersonaChooseModal.tsx

import React from "react";
import { Modal } from "../Modal";
import { Persona } from "../../types";

type Props = {
  open: boolean;
  onClose: () => void;

  predefined: Persona[];
  customPersonas: Persona[];
  activePersonas: Persona[];

  onDeletePersona: (id: string) => void;
  onChoosePersona: (persona: Persona) => void;

  setPersonaToConfirm: (p: Persona | null) => void;
  renderIcon: (key: string, className?: string) => JSX.Element;
};

export const PersonaChooseModal: React.FC<Props> = ({
  open,
  onClose,
  predefined,
  customPersonas,
  activePersonas,
  onDeletePersona,
  onChoosePersona,
  setPersonaToConfirm,
  renderIcon,
}) => {
  const selectable = [...predefined, ...customPersonas]
  .filter(p => !activePersonas.some(ap => ap.name === p.name));

  return (
    <Modal open={open} onClose={onClose}>
      <h3 className="text-lg font-semibold text-purple-100 mb-4">
        Select a Persona
      </h3>

      {selectable.length === 0 && (
        <p className="text-center text-purple-300 py-6">
          You are using all the personas.
        </p>
      )}

      {selectable.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {selectable.map((p) => (
            <div key={p.id} className="relative group">
              <button
                onClick={() => setPersonaToConfirm(p)}
                className="w-full h-20 flex items-center justify-center 
                rounded-xl border border-purple-800 
                bg-black/40 hover:bg-purple-900/30 
                transition shadow-md p-2"
              >
                {renderIcon(p.icon, "w-8 h-8 text-purple-200")}
              </button>

              {/* Delete button */}
              <button
                className="absolute -top-2 -right-2 h-6 w-6 flex items-center justify-center 
                rounded-full bg-red-600 hover:bg-red-500 
                text-white text-xs shadow-lg shadow-red-900/40
                transition-transform transform hover:scale-110"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeletePersona(p.id);
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
};
