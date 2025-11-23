// src/components/persona-panel/PersonaCreateModal.tsx

import React from "react";
import { Modal } from "../Modal";

type Props = {
  open: boolean;
  onClose: () => void;

  showManualForm: boolean;
  setShowManualForm: (value: boolean) => void;

  name: string;
  setName: (v: string) => void;

  description: string;
  setDescription: (v: string) => void;

  handleAdd: () => void;

  handleCVUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
};

export const PersonaCreateModal: React.FC<Props> = ({
  open,
  onClose,
  showManualForm,
  setShowManualForm,
  name,
  setName,
  description,
  setDescription,
  handleAdd,
  handleCVUpload,
}) => {
  return (
    <Modal
      open={open}
      onClose={() => {
        onClose();
        setShowManualForm(false);
      }}
    >
      {!showManualForm ? (
        <div className="text-center space-y-4">
          <h3 className="text-lg font-semibold text-purple-100 mb-2">
            Create a Persona
          </h3>

          <button
            className="w-full rounded-xl bg-purple-700 text-white py-2"
            onClick={() => setShowManualForm(true)}
          >
            Add Manually
          </button>

          {/* CV Upload */}
          <input
            id="cv-upload"
            type="file"
            accept=".pdf,.doc,.docx"
            className="hidden"
            onChange={handleCVUpload}
          />
          <label
            htmlFor="cv-upload"
            className="w-full block rounded-xl bg-purple-600 text-white py-2 text-center cursor-pointer"
          >
            Upload CV
          </label>
        </div>
      ) : (
        <div className="max-h-[70vh] flex flex-col space-y-3 overflow-y-auto">
          <div className="flex-1 space-y-3">
            <h3 className="text-lg font-semibold text-purple-100 mb-4">
              Add Persona Manually
            </h3>

            <input
              className="w-full rounded-xl border border-purple-900/50 bg-black/70 px-3 py-2 text-sm text-purple-100"
              placeholder="Persona name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />

            <textarea
              className="w-full h-24 rounded-xl border border-purple-900/50 bg-black/70 px-3 py-2 text-sm text-purple-100"
              placeholder="Persona description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="sticky bottom-0 bg-black/80 pt-3 flex gap-2">
            <button
              onClick={handleAdd}
              className="w-full rounded-xl bg-fuchsia-600 text-white py-2"
            >
              Add Persona
            </button>

            <button
              onClick={() => setShowManualForm(false)}
              className="w-full rounded-xl bg-black/40 border border-purple-800 text-purple-300 py-2"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
};
