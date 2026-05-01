import React, { useState } from "react";
import { Modal } from "../Modal";

const btnPrimary =
  "rounded-xl bg-purple-700 hover:bg-purple-600 text-white py-2 font-medium transition-colors";
const btnPrimaryLabel = `${btnPrimary} w-full block text-center cursor-pointer`;

type SearchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; name: string; title: string; description: string }
  | { status: "error"; message: string };

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
  onSearchResearcher: (name: string) => Promise<void>;
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
  onSearchResearcher,
}) => {
  const [showSearchForm, setShowSearchForm] = useState(false);
  const [searchName, setSearchName] = useState("");
  const [searchState, setSearchState] = useState<SearchState>({ status: "idle" });

  const resetSearch = () => {
    setShowSearchForm(false);
    setSearchName("");
    setSearchState({ status: "idle" });
  };

  const handleClose = () => {
    onClose();
    setShowManualForm(false);
    resetSearch();
  };

  const handleSearch = async () => {
    if (!searchName.trim()) return;
    setSearchState({ status: "loading" });
    try {
      await onSearchResearcher(searchName.trim());
      handleClose();
    } catch (err) {
      setSearchState({
        status: "error",
        message: err instanceof Error ? err.message : "Search failed.",
      });
    }
  };

  if (showSearchForm) {
    return (
      <Modal open={open} onClose={handleClose}>
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-purple-100">Search Researcher</h3>
          <p className="text-xs text-purple-300/70">
            Enter a researcher's name to search Google Scholar, scrape their publications, and build a persona automatically.
          </p>

          <input
            className="w-full rounded-xl border border-purple-900/50 bg-black/70 px-3 py-2 text-sm text-purple-100 placeholder:text-purple-500"
            placeholder="e.g. Steffen Herbold"
            value={searchName}
            onChange={(e) => setSearchName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            disabled={searchState.status === "loading"}
          />

          {searchState.status === "loading" && (
            <div className="rounded-xl border border-purple-800/40 bg-black/40 p-4 text-center space-y-2">
              <span className="flex items-center justify-center gap-2 text-sm text-fuchsia-200">
                <span className="h-2 w-2 animate-pulse rounded-full bg-fuchsia-400" />
                Scraping publications and building persona…
              </span>
              <p className="text-xs text-purple-400/70">This may take a minute.</p>
            </div>
          )}

          {searchState.status === "error" && (
            <p className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-200">
              {searchState.message}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={handleSearch}
              disabled={!searchName.trim() || searchState.status === "loading"}
              className="flex-1 rounded-xl bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white py-2 font-medium transition-colors"
            >
              {searchState.status === "loading" ? "Searching…" : "Search"}
            </button>
            <button
              type="button"
              onClick={resetSearch}
              disabled={searchState.status === "loading"}
              className="flex-1 rounded-xl bg-black/40 border border-purple-800 hover:border-purple-600 text-purple-200 py-2 font-medium transition-colors"
            >
              Back
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={handleClose}>
      {!showManualForm ? (
        <div className="text-center space-y-4">
          <h3 className="text-lg font-semibold text-purple-100 mb-2">Create a Persona</h3>

          <button type="button" className={`${btnPrimary} w-full`} onClick={() => setShowManualForm(true)}>
            Add Manually
          </button>

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

          <button
            type="button"
            className={`${btnPrimary} w-full`}
            onClick={() => setShowSearchForm(true)}
          >
            Search Researcher
          </button>
        </div>
      ) : (
        <div className="max-h-[70vh] flex flex-col space-y-3 overflow-y-auto">
          <div className="flex-1 space-y-3">
            <h3 className="text-lg font-semibold text-purple-100 mb-4">Add Persona Manually</h3>
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
            <button type="button" onClick={handleAdd} className={`${btnPrimary} flex-1`}>
              Add Persona
            </button>
            <button
              type="button"
              onClick={() => setShowManualForm(false)}
              className="flex-1 rounded-xl bg-black/40 border border-purple-800 hover:border-purple-600 text-purple-200 hover:text-purple-100 py-2 font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
};
