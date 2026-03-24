import React, { useCallback, useEffect, useState } from "react";
import { Persona } from "../types";
import { Modal } from "./Modal";
import { ICON_OPTIONS } from "../constants/icons";
import { PersonaIconSelector } from "./persona-panel/PersonaIconModal.tsx";
import { PersonaEditor } from "./persona-panel/PersonaEditor.tsx";
import { PersonaChooseModal } from "./persona-panel/PersonaChooseModal";
import { PersonaGrid } from "./persona-panel/PersonaGrid";
import {
  PersonaCreateModal,
  iconNameForScholarId,
} from "./persona-panel/PersonaCreateModal";
import {
  mergeBundledResearchSnapshots,
  type ResearchSnapshotRow,
} from "../data/bundledResearchers";
import { PersonaViewModal } from "./persona-panel/PersonaViewModal";

import { API_BASE_URL } from "../config.ts";
import { toast } from "react-toastify";

type Props = {
  personas: Persona[];
  onAddPersona: (persona: Omit<Persona, "id">) => void;
  onRemovePersona: (id: string) => void;
  onUpdatePersona: (updated: Persona) => void;
};

export const PersonaPanel: React.FC<Props> = ({
  personas,
  onAddPersona,
  onRemovePersona,
  onUpdatePersona,
}) => {
  const [customPersonas, setCustomPersonas] = useState<Persona[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editedIcon, setEditedIcon] = useState("User");
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [showChoosePersona, setShowChoosePersona] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showManualForm, setShowManualForm] = useState(false);
  const [iconModalOpen, setIconModalOpen] = useState(false);
  const [personaToConfirm, setPersonaToConfirm] = useState<Persona | null>(
    null
  );
  const [researchSnapshots, setResearchSnapshots] = useState<
    ResearchSnapshotRow[]
  >([]);
  const [savedResearchersOpen, setSavedResearchersOpen] = useState(false);

  const renderIcon = (
    key: string,
    className = "w-5 h-5 text-purple-300 mx-auto"
  ) => {
    const IconEntry = ICON_OPTIONS.find((opt) => opt.name === key);
    const Icon = IconEntry?.Component ?? ICON_OPTIONS[0].Component;
    return <Icon className={className} />;
  };

  const handleAdd = () => {
    if (!name.trim() || !description.trim()) return;

    const newPersona = { name, description, icon: editedIcon };

    onAddPersona(newPersona);
    setCustomPersonas((prev) => [
      ...prev,
      { ...newPersona, id: Date.now().toString() },
    ]);

    toast.success("Persona created successfully!");

    setName("");
    setDescription("");
  };

  const predefined = [
    {
      id: "junior",
      name: "Junior Software Engineer",
      description:
        "1 year experience, recently graduated, focuses on quick solutions",
      icon: "User",
    },
    {
      id: "senior",
      name: "Senior Software Engineer",
      description:
        "10 years experience, prioritizes scalability and maintainability",
      icon: "UserStar",
    },
  ];

  useEffect(() => {
    if (!showCreateModal) {
      setSavedResearchersOpen(false);
      setResearchSnapshots([]);
    }
  }, [showCreateModal]);

  const handleToggleSavedResearchers = useCallback(() => {
    if (savedResearchersOpen) {
      setSavedResearchersOpen(false);
      return;
    }
    setSavedResearchersOpen(true);
    // Always show bundled examples immediately (no empty state while loading).
    setResearchSnapshots(mergeBundledResearchSnapshots([]));
    fetch(`${API_BASE_URL}/api/research/raw-authors`)
      .then(async (r) => {
        if (!r.ok) {
          const hint =
            r.status === 404
              ? "Backend route missing — restart the API or update the backend."
              : `Could not load list (HTTP ${r.status}). Is the API at ${API_BASE_URL} running?`;
          throw new Error(hint);
        }
        return r.json();
      })
      .then((data) => {
        if (!Array.isArray(data)) {
          toast.error("Unexpected response from server when loading researchers.");
          setResearchSnapshots(mergeBundledResearchSnapshots([]));
          return;
        }
        setResearchSnapshots(mergeBundledResearchSnapshots(data));
      })
      .catch((err) => {
        console.error(err);
        setResearchSnapshots(mergeBundledResearchSnapshots([]));
        toast.error(
          err instanceof Error
            ? err.message
            : "Network error — check the backend is running and VITE_API_BASE_URL."
        );
      });
  }, [savedResearchersOpen]);

  const applyResearchPersonaPayload = (
    data: {
      name?: string;
      title?: string;
      description?: string;
    },
    options?: { icon?: string }
  ) => {
    const personaName = data.title || data.name || "Unnamed Persona";
    const personaDescription = data.description || "No description provided.";
    const icon = options?.icon ?? "User";
    const newPersona = {
      id: Date.now().toString(),
      name: personaName,
      description: personaDescription,
      icon,
    };
    setCustomPersonas((prev) => [...prev, newPersona]);
    onAddPersona({
      name: newPersona.name,
      description: newPersona.description,
      icon: newPersona.icon,
    });
    toast.success("Persona added");
    setShowCreateModal(false);
    setShowManualForm(false);
  };

  const handleResearchJsonUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE_URL}/api/persona/from-research-json`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      const data = await res.json();
      applyResearchPersonaPayload(data);
    } catch (err) {
      console.error(err);
      toast.error("Couldn’t create persona from that file.");
    } finally {
      event.target.value = "";
    }
  };

  const handleSelectResearchSnapshot = async (scholarId: string) => {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/persona/from-research-snapshot/${encodeURIComponent(
          scholarId
        )}`,
        { method: "POST" }
      );
      if (!res.ok) throw new Error(`Snapshot failed: ${res.status}`);
      const data = await res.json();
      applyResearchPersonaPayload(data, {
        icon: iconNameForScholarId(scholarId),
      });
    } catch (err) {
      console.error(err);
      toast.error("Couldn’t create persona from that researcher.");
    }
  };

  const handleCVUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE_URL}/api/persona/from-cv`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Upload failed: ${res.status}`);
      }

      const data = await res.json();

      // Expecting backend to return: { name, title, description }
      const personaName = data.title || data.name || "Unnamed Persona";
      const personaDescription = data.description || "No description provided.";

      // Create new persona object for pool
      const newPersona = {
        id: Date.now().toString(),
        name: personaName,
        description: personaDescription,
        icon: "User",
      };

      // Add to persona pool
      setCustomPersonas((prev) => [...prev, newPersona]);

      // Immediately activate this persona
      onAddPersona({
        name: newPersona.name,
        description: newPersona.description,
        icon: newPersona.icon,
      });

      toast.success("CV persona added");

      // Close modal + reset manual form state if open
      setShowCreateModal(false);
      setShowManualForm(false);
    } catch (err) {
      console.error(err);
      toast.error("Failed to create persona from CV.");
    } finally {
      // allow re-uploading the same file again
      event.target.value = "";
    }
  };

  return (
    <article className="rounded-3xl border border-purple-900/40 bg-black/60 p-6 shadow-xl shadow-purple-950/30 backdrop-blur">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-purple-100">Personas</h2>
          <p className="text-sm text-purple-300/70">
            Define the specialist viewpoints for this discussion.
          </p>
        </div>
        <span className="rounded-full border border-purple-800/30 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-purple-300/70">
          {personas.length} active
        </span>
      </div>

      {/* Grid */}
      <PersonaGrid
        personas={personas}
        onSelectPersona={setSelectedPersona}
        renderIcon={renderIcon}
      />

      {/* Action Buttons */}
      <div className="mt-6 flex gap-3">
        <button
          onClick={() => setShowChoosePersona(true)}
          className="rounded-xl px-4 py-2 bg-purple-700 text-white"
        >
          Choose a Persona
        </button>
        <button
          onClick={() => setShowCreateModal(true)}
          className="rounded-xl px-4 py-2 bg-fuchsia-600 text-white"
        >
          Create a Persona
        </button>
      </div>

      {/* Choose Modal */}
      <PersonaChooseModal
        open={showChoosePersona}
        onClose={() => setShowChoosePersona(false)}
        predefined={predefined}
        customPersonas={customPersonas}
        activePersonas={personas}
        onDeletePersona={(id) => {
          setCustomPersonas((prev) => prev.filter((p) => p.id !== id));
          const index = predefined.findIndex((p) => p.id === id);
          if (index !== -1) predefined.splice(index, 1);
        }}
        onChoosePersona={(p) =>
          onAddPersona({
            name: p.name,
            description: p.description,
            icon: p.icon,
          })
        }
        setPersonaToConfirm={setPersonaToConfirm}
        renderIcon={renderIcon}
      />

      {/* Create Modal */}
      <PersonaCreateModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        showManualForm={showManualForm}
        setShowManualForm={setShowManualForm}
        name={name}
        setName={setName}
        description={description}
        setDescription={setDescription}
        handleAdd={() => {
          handleAdd();
          setShowCreateModal(false);
          setShowManualForm(false);
        }}
        handleCVUpload={handleCVUpload}
        handleResearchJsonUpload={handleResearchJsonUpload}
        researchSnapshots={researchSnapshots}
        savedResearchersOpen={savedResearchersOpen}
        onToggleSavedResearchers={handleToggleSavedResearchers}
        onSelectResearchSnapshot={handleSelectResearchSnapshot}
        renderIcon={renderIcon}
      />

      {/* Selected Persona Modal */}
      <PersonaViewModal
        open={!!selectedPersona && !isEditing}
        persona={selectedPersona}
        onClose={() => setSelectedPersona(null)}
        onEdit={() => setIsEditing(true)}
        onRemove={(id) => {
          onRemovePersona(id);
          setSelectedPersona(null);
        }}
        renderIcon={renderIcon}
      />

      {/* Edit Modal */}
      <Modal
        open={!!selectedPersona && isEditing}
        onClose={() => setIsEditing(false)}
        showCloseButton={false}
      >
        {selectedPersona && (
          <PersonaEditor
            persona={selectedPersona}
            icon={editedIcon}
            onOpenIconModal={() => setIconModalOpen(true)}
            onCancel={() => setIsEditing(false)}
            onSave={(updated) => {
              onUpdatePersona(updated);
              setSelectedPersona(updated);
              setIsEditing(false);
            }}
            renderIcon={renderIcon}
          />
        )}
      </Modal>

      {/* Icon Modal */}
      <Modal open={iconModalOpen} onClose={() => setIconModalOpen(false)}>
        <h3 className="text-lg font-semibold text-purple-100 mb-4">
          Select Icon
        </h3>
        <PersonaIconSelector
          selected={editedIcon}
          onSelect={(icon) => {
            setEditedIcon(icon);
            setIconModalOpen(false);
          }}
          options={ICON_OPTIONS}
        />
      </Modal>
      {/* Confirm Persona Select */}
      <Modal
        open={!!personaToConfirm}
        onClose={() => setPersonaToConfirm(null)}
      >
        {personaToConfirm && (
          <div className="text-center space-y-4">
            {renderIcon(
              personaToConfirm.icon,
              "w-14 h-14 text-fuchsia-300 mx-auto"
            )}

            <h3 className="text-lg font-semibold text-purple-100">
              Use this Persona?
            </h3>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => {
                  onAddPersona({
                    name: personaToConfirm.name,
                    description: personaToConfirm.description,
                    icon: personaToConfirm.icon,
                  });
                  setPersonaToConfirm(null);
                  setShowChoosePersona(false);
                }}
                className="w-full rounded-xl bg-fuchsia-600 text-white py-2"
              >
                Select
              </button>

              <button
                onClick={() => setPersonaToConfirm(null)}
                className="w-full rounded-xl bg-black/40 border border-purple-800 text-purple-300 py-2"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </Modal>
    </article>
  );
};
