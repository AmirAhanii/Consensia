import React, { useEffect, useRef, useState } from "react";
import { Camera, FileText, Plus, Send, X } from "lucide-react";
import { debateComposerBar, debateComposerTextarea } from "../theme/themeClasses";

type Props = {
  question: string;
  onChange: (value: string) => void;
  attachments: File[];
  onAttachmentsChange: (files: File[]) => void;
  onRun: () => void;
  canRun: boolean;
  isLoading: boolean;
};

export const DebateComposer: React.FC<Props> = ({
  question,
  onChange,
  attachments,
  onAttachmentsChange,
  onRun,
  canRun,
  isLoading,
}) => {
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [question]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canRun) onRun();
    }
  };

  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menuOpen]);

  const addFiles = (incoming: File[]) => {
    const allowed = incoming.filter((f) => {
      const name = (f.name || "").toLowerCase();
      const t = (f.type || "").toLowerCase();
      return (
        t.startsWith("image/") ||
        t === "application/pdf" ||
        name.endsWith(".pdf") ||
        name.endsWith(".docx")
      );
    });
    if (allowed.length === 0) return;
    const merged = [...attachments, ...allowed].slice(0, 8);
    onAttachmentsChange(merged);
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-3 py-2 sm:px-4">
      <div
        className={debateComposerBar}
        onDragOver={(e) => {
          e.preventDefault();
        }}
        onDrop={(e) => {
          e.preventDefault();
          const dropped = Array.from(e.dataTransfer.files || []);
          addFiles(dropped);
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept="image/*,application/pdf,.docx"
          className="hidden"
          disabled={isLoading}
          onChange={(e) => {
            const files = Array.from(e.currentTarget.files || []);
            addFiles(files);
            e.currentTarget.value = "";
          }}
          multiple
        />
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          disabled={isLoading}
          onChange={(e) => {
            const files = Array.from(e.currentTarget.files || []);
            addFiles(files);
            e.currentTarget.value = "";
          }}
        />

        <div ref={menuRef} className="relative shrink-0">
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            disabled={isLoading}
            title="Add attachment"
            className="flex h-11 w-11 items-center justify-center rounded-full border border-[color:var(--c-border-soft)] bg-[var(--c-surface-ghost)] text-[var(--c-fg)] transition hover:border-[color:var(--c-border-strong)] hover:bg-[var(--c-surface-ghost-hover)] disabled:opacity-40"
          >
            <Plus className="h-5 w-5" aria-hidden />
          </button>

          {menuOpen ? (
            <div className="absolute left-0 top-[calc(100%+0.5rem)] z-50 w-44 overflow-hidden rounded-2xl border border-[color:var(--c-border)] bg-[var(--c-surface-dropdown)] p-1 shadow-xl shadow-black/40 backdrop-blur-md">
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  fileRef.current?.click();
                }}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-[var(--c-fg)] transition hover:bg-[var(--c-surface-nav-hover)]"
              >
                <FileText className="h-4 w-4 text-[var(--c-fg-hint)]" aria-hidden />
                File
              </button>
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  cameraRef.current?.click();
                }}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-[var(--c-fg)] transition hover:bg-[var(--c-surface-nav-hover)]"
              >
                <Camera className="h-4 w-4 text-[var(--c-fg-hint)]" aria-hidden />
                Camera
              </button>
            </div>
          ) : null}
        </div>
        <textarea
          ref={taRef}
          rows={1}
          className={debateComposerTextarea}
          placeholder="Ask anything…"
          value={question}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        {attachments.length > 0 ? (
          <div className="flex max-w-[46%] flex-wrap items-center justify-end gap-2">
            {attachments.map((f, idx) => (
              <div
                key={`${f.name}-${f.size}-${idx}`}
                className="flex items-center gap-2 rounded-full border border-[color:var(--c-border-soft)] bg-[var(--c-surface-ghost)] px-3 py-1.5 text-xs text-[var(--c-fg)]"
              >
                <span className="max-w-[140px] truncate">{f.name}</span>
                <button
                  type="button"
                  onClick={() => onAttachmentsChange(attachments.filter((_, i) => i !== idx))}
                  disabled={isLoading}
                  className="rounded-full p-1 text-[var(--c-fg-hint)] hover:text-[var(--c-fg)] disabled:opacity-40"
                  title="Remove attachment"
                >
                  <X className="h-3.5 w-3.5" aria-hidden />
                </button>
              </div>
            ))}
          </div>
        ) : null}
        <button
          type="button"
          onClick={onRun}
          disabled={!canRun}
          title={canRun ? "Run debate (Enter)" : "Add a question and at least one persona"}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-fuchsia-500 to-purple-600 text-white shadow-lg shadow-purple-900/50 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40 light:shadow-violet-300/40"
        >
          {isLoading ? (
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          ) : (
            <Send className="h-5 w-5 translate-x-px" aria-hidden />
          )}
        </button>
      </div>
    </div>
  );
};
