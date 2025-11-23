import React from "react";
import { Modal } from "../Modal";
import { Persona } from "../../types";

type Props = {
  open: boolean;
  persona: Persona | null;
  onClose: () => void;
  onEdit: () => void;
  onRemove: (id: string) => void;
  renderIcon: (key: string, className?: string) => JSX.Element;
};

export const PersonaViewModal: React.FC<Props> = ({
  open,
  persona,
  onClose,
  onEdit,
  onRemove,
  renderIcon,
}) => {
  if (!persona) return null;

  return (
    <Modal open={open} onClose={onClose}>
      <div className="text-center">
        {renderIcon(persona.icon, "w-16 h-16 text-fuchsia-300 mx-auto")}
        <h3 className="mt-3 text-xl font-semibold text-purple-100">{persona.name}</h3>
        <p className="mt-2 text-sm text-purple-300">{persona.description}</p>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <button
            onClick={onEdit}
            className="rounded-xl bg-purple-700 text-white py-2"
          >
            Edit
          </button>
          <button
            onClick={() => onRemove(persona.id)}
            className="rounded-xl bg-fuchsia-600 text-white py-2"
          >
            Remove
          </button>
        </div>
      </div>
    </Modal>
  );
};
