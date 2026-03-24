// src/components/persona-panel/PersonaCreateModal.tsx

import React from "react";
import { Modal } from "../Modal";
import { ICON_OPTIONS } from "../../constants/icons";
import type { ResearchSnapshotRow } from "../../data/bundledResearchers";

export type { ResearchSnapshotRow };

export function iconNameForScholarId(scholarId: string): string {
  let h = 0;
  for (let i = 0; i < scholarId.length; i++) {
    h = (h * 31 + scholarId.charCodeAt(i)) >>> 0;
  }
  return ICON_OPTIONS[h % ICON_OPTIONS.length]!.name;
}

/** Same primary style as Modal Close + main persona actions */
const btnPrimary =
  "w-full rounded-xl bg-purple-700 hover:bg-purple-600 text-white py-2 font-medium transition-colors";
const btnPrimaryLabel = `${btnPrimary} block text-center cursor-pointer`;

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

  /** Researcher snapshot file → persona (same flow as CV). */
  handleResearchJsonUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
  researchSnapshots: ResearchSnapshotRow[];
  savedResearchersOpen: boolean;
  onToggleSavedResearchers: () => void;
  onSelectResearchSnapshot: (scholarId: string) => void;
  renderIcon: (key: string, className?: string) => React.ReactElement;
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
  handleResearchJsonUpload,
  researchSnapshots,
  savedResearchersOpen,
  onToggleSavedResearchers,
  onSelectResearchSnapshot,
  renderIcon,
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
            type="button"
            className={btnPrimary}
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
          <label htmlFor="cv-upload" className={btnPrimaryLabel}>
            Upload CV
          </label>

          <input
            id="research-json-upload"
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={handleResearchJsonUpload}
          />
          <label htmlFor="research-json-upload" className={btnPrimaryLabel}>
            Upload researcher file
          </label>

          <button
            type="button"
            className={btnPrimary}
            onClick={onToggleSavedResearchers}
          >
            {savedResearchersOpen ? "Hide saved researchers" : "Saved researchers"}
          </button>

          {savedResearchersOpen ? (
            <div className="text-left rounded-xl border border-purple-800/50 bg-black/40 p-3 space-y-3">
              <p className="text-sm text-purple-200/90 font-medium">
                Choose a researcher
              </p>
              {researchSnapshots.length === 0 ? (
                <p className="text-sm text-purple-400/90 py-4 text-center">
                  No researchers to show.
                </p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-[min(52vh,22rem)] overflow-y-auto pr-1">
                  {researchSnapshots.map((row) => {
                    const iconKey = iconNameForScholarId(row.scholar_id);
                    const displayName = row.name?.trim() || "Researcher";
                    return (
                      <button
                        type="button"
                        key={row.scholar_id}
                        onClick={() => onSelectResearchSnapshot(row.scholar_id)}
                        className="flex flex-col items-center gap-2 rounded-xl border border-purple-900/50 bg-black/50 hover:bg-purple-900/35 p-3 text-center transition shadow-md min-h-[7.5rem]"
                      >
                        {renderIcon(iconKey, "w-9 h-9 text-purple-200 shrink-0")}
                        <span className="text-xs font-semibold text-purple-100 leading-tight line-clamp-2 w-full">
                          {displayName}
                        </span>
                        {row.affiliation ? (
                          <span className="text-[10px] text-purple-300/85 leading-snug line-clamp-2 w-full">
                            {row.affiliation}
                          </span>
                        ) : null}
                        {row.preview ? (
                          <span className="text-[10px] text-purple-400/75 leading-snug line-clamp-2 w-full text-left">
                            {row.preview}
                          </span>
                        ) : null}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ) : null}
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
              type="button"
              onClick={handleAdd}
              className={btnPrimary}
            >
              Add Persona
            </button>

            <button
              type="button"
              onClick={() => setShowManualForm(false)}
              className="w-full rounded-xl bg-black/40 border border-purple-800 hover:border-purple-600 text-purple-200 hover:text-purple-100 py-2 font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
};
