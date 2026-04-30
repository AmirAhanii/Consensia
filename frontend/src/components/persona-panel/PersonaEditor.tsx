import React, { useEffect, useState } from "react";
import { Persona } from "../../types";

type Props = {
  persona: Persona;
  icon: string;
  onOpenIconModal: () => void;
  onCancel: () => void;
  onSave: (updated: Persona) => void;
  renderIcon: (icon: string, className?: string) => JSX.Element;
  /** When false, hide the separate "Change icon" control (parent provides icon UI). */
  showIconButton?: boolean;
};

export const PersonaEditor: React.FC<Props> = ({
  persona,
  icon,
  onOpenIconModal,
  onCancel,
  onSave,
  renderIcon,
  showIconButton = true,
}) => {
  const [name, setName] = useState(persona.name);
  const [description, setDescription] = useState(persona.description);
  const [personaBasis, setPersonaBasis] = useState(persona.personaBasis ?? "");

  useEffect(() => {
    setName(persona.name);
    setDescription(persona.description);
    setPersonaBasis(persona.personaBasis ?? "");
  }, [persona]);

  const inputClass =
    "w-full rounded-xl border border-purple-900/50 bg-black/60 px-3 py-2 text-sm text-purple-100 placeholder:text-purple-600 outline-none transition-colors focus:border-fuchsia-500/40 focus:ring-1 focus:ring-fuchsia-500/25 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-field)] light:text-[var(--c-fg)]";
  const canSave = name.trim().length > 0 && description.trim().length > 0;

  return (
    <div className="space-y-3">
      {showIconButton && (
        <div>
          <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-purple-500 light:text-violet-600">
            Icon
          </p>
          <button
            type="button"
            onClick={onOpenIconModal}
            className="inline-flex items-center gap-2 rounded-xl border border-purple-800/40 bg-black/40 px-3 py-2 text-sm font-medium text-purple-200 transition-colors duration-200 hover:border-purple-600/50 hover:bg-purple-950/30 hover:text-purple-50 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-inline)] light:text-[var(--c-fg)]"
          >
            {renderIcon(icon, "h-5 w-5 shrink-0 text-fuchsia-300")}
            <span>Change icon</span>
          </button>
        </div>
      )}

      <div>
        <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-purple-500 light:text-violet-600">
          Name
        </p>
        <input
          type="text"
          className={inputClass}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Persona name"
        />
      </div>

      <div>
        <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-purple-500 light:text-violet-600">
          Description
        </p>
        <textarea
          className={`min-h-[88px] resize-y ${inputClass}`}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="How they argue, expertise, tone…"
        />
      </div>

      <div>
        <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-purple-500 light:text-violet-600">
          Source material (optional)
        </p>
        <p className="mb-1.5 text-[10px] leading-snug text-purple-500/80 light:text-violet-600/85">
          Paste CV excerpts, researcher profile text, or anything else used to define this debater.
          The judge uses it for topic-fit scoring (0–9) before the debate and does not hard-code role
          assumptions.
        </p>
        <textarea
          className={`min-h-[72px] resize-y ${inputClass}`}
          value={personaBasis}
          onChange={(e) => setPersonaBasis(e.target.value)}
          placeholder="Leave empty to use only the description above."
        />
      </div>

      <div className="flex gap-2 border-t border-purple-800/25 pt-3 light:border-violet-200/55">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 rounded-xl border border-purple-800/50 bg-black/35 py-2 text-sm font-medium text-purple-200 transition-colors duration-200 hover:border-purple-600/45 hover:bg-purple-950/40 hover:text-purple-50 light:border-[color:var(--c-border)] light:bg-[var(--c-surface-ghost)] light:text-[var(--c-fg)]"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() =>
            onSave({
              ...persona,
              name: name.trim(),
              description: description.trim(),
              icon,
              personaBasis: personaBasis.trim() || undefined,
            })
          }
          disabled={!canSave}
          className="flex-1 rounded-xl bg-gradient-to-r from-purple-600 to-fuchsia-600 py-2 text-sm font-semibold text-white shadow-md shadow-purple-950/40 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Save changes
        </button>
      </div>
    </div>
  );
};
