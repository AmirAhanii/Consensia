import React, { useState } from "react";
import { Persona } from "../../types";

type Props = {
  persona: Persona;
  icon: string;
  onOpenIconModal: () => void;
  onCancel: () => void;
  onSave: (updated: Persona) => void;
  renderIcon: (icon: string, className?: string) => JSX.Element;
};

export const PersonaEditor: React.FC<Props> = ({
  persona,
  icon,
  onOpenIconModal,
  onCancel,
  onSave,
  renderIcon,
}) => {
  const [name, setName] = useState(persona.name);
  const [description, setDescription] = useState(persona.description);

  return (
<div className="flex flex-col max-h-[80vh]">
      {/* Scrollable fields section */}
<div className="flex-1 overflow-y-auto p-4 space-y-2">
        <h3 className="text-lg font-semibold text-purple-100">Edit Persona</h3>

        <div>
          <label className="text-sm text-purple-300 block mb-1">Choose Icon</label>
          <button onClick={onOpenIconModal} className="flex items-center gap-2 text-purple-400 hover:underline">
            {renderIcon(icon)}
            <span>Change Icon</span>
          </button>
        </div>

        <div>
          <label className="text-sm text-purple-300 block mb-1">Title</label>
          <input
            className="w-full rounded-xl border border-purple-900/50 bg-black/70 px-3 py-2 text-sm text-purple-100"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div>
          <label className="text-sm text-purple-300 block mb-1">Description</label>
          <textarea
            className="w-full h-20 rounded-xl border border-purple-900/50 bg-black/70 px-3 py-2 text-sm text-purple-100"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>

      {/* Sticky footer */}
      <div className="flex gap-2 px-4 py-3 border-t border-purple-800/30 bg-black/70">
        <button
          onClick={() => onSave({ ...persona, name, description, icon })}
          className="w-full rounded-xl bg-fuchsia-600 text-white py-2"
        >
          Save
        </button>
        <button
          onClick={onCancel}
          className="w-full rounded-xl bg-black/40 border border-purple-800 text-purple-300 py-2"
        >
          Cancel
        </button>
      </div>
    </div>
  );
};
