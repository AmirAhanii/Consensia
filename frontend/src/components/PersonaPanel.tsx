import React, { useState } from "react";
import { Persona } from "../types";

type PersonaPanelProps = {
  personas: Persona[];
  onAddPersona: (persona: Omit<Persona, "id">) => void;
  onRemovePersona: (id: string) => void;
};

export const PersonaPanel: React.FC<PersonaPanelProps> = ({ personas, onAddPersona, onRemovePersona }) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = () => {
    if (!name.trim() || !description.trim()) return;
    onAddPersona({ name: name.trim(), description: description.trim() });
    setName("");
    setDescription("");
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <article className="rounded-3xl border border-purple-900/40 bg-black/60 p-6 shadow-xl shadow-purple-950/30 backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-purple-100">Personas</h2>
          <p className="text-sm text-purple-300/70">Define the specialist viewpoints for this discussion.</p>
        </div>
        <span className="rounded-full border border-purple-800/30 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-purple-300/70">
          {personas.length} active
        </span>
      </div>

      <div className="mt-5 space-y-4">
        {personas.map((persona) => (
          <div
            key={persona.id}
            className="group relative overflow-hidden rounded-2xl border border-purple-900/40 bg-gradient-to-br from-purple-950/50 to-black/60 p-4 shadow-inner shadow-black/40"
          >
            <div className="absolute inset-0 opacity-0 transition group-hover:opacity-100">
              <div className="h-full w-full bg-[radial-gradient(circle_at_top_left,rgba(236,72,153,0.14),transparent_60%)]" />
            </div>
            <div className="relative flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-purple-100">{persona.name}</p>
                <p className="mt-1 text-xs leading-relaxed text-purple-300/70">{persona.description}</p>
              </div>
              <button
                onClick={() => onRemovePersona(persona.id)}
                className="rounded-full border border-transparent px-3 py-1 text-xs font-medium text-purple-300/60 transition hover:border-fuchsia-500/40 hover:text-fuchsia-200"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 space-y-3 rounded-2xl border border-dashed border-purple-900/50 bg-black/40 p-5">
        <h3 className="text-sm font-semibold text-purple-200">Add persona</h3>
        <div className="grid gap-3">
          <input
            className="rounded-xl border border-purple-900/50 bg-black/70 px-3 py-2 text-sm text-purple-100 outline-none transition focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40"
            placeholder="Persona name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <textarea
            className="h-28 rounded-xl border border-purple-900/50 bg-black/70 px-3 py-2 text-sm text-purple-100 outline-none transition focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40"
            placeholder="Persona background, experience, traits"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-purple-300/70">
          <span>Tip: Press ⌘/Ctrl + Enter to add quickly.</span>
          <button
            onClick={handleSubmit}
            className="rounded-full border border-fuchsia-500/40 bg-gradient-to-r from-purple-600/40 to-fuchsia-500/40 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-fuchsia-100 transition hover:from-purple-500/50 hover:to-fuchsia-400/50"
          >
            Add Persona
          </button>
        </div>
      </div>
    </article>
  );
};

