import React, { useEffect, useRef, useState } from "react";
import { Camera, FileText, GripVertical, Plus, Send, X } from "lucide-react";
import { MAX_DEBATE_ATTACHMENT_TOTAL_BYTES } from "../config";
import { debateComposerBar, debateComposerTextarea } from "../theme/themeClasses";

function formatMb(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return mb >= 10 ? mb.toFixed(1) : mb.toFixed(2);
}

type Props = {
  question: string;
  onChange: (value: string) => void;
  attachments: File[];
  onAttachmentsChange: (files: File[]) => void;
  onRun: () => void;
  canRun: boolean;
  isLoading: boolean;
  attachmentTotalBytes: number;
  maxAttachmentTotalBytes?: number;
};

export const DebateComposer: React.FC<Props> = ({
  question,
  onChange,
  attachments,
  onAttachmentsChange,
  onRun,
  canRun,
  isLoading,
  attachmentTotalBytes,
  maxAttachmentTotalBytes = MAX_DEBATE_ATTACHMENT_TOTAL_BYTES,
}) => {
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const dragDepth = useRef(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isFileDragging, setIsFileDragging] = useState(false);
  const [attachmentPreviewUrls, setAttachmentPreviewUrls] = useState<(string | null)[]>([]);
  const [dragOverTileIndex, setDragOverTileIndex] = useState<number | null>(null);

  useEffect(() => {
    const next = attachments.map((f) =>
      f.type.startsWith("image/") ? URL.createObjectURL(f) : null,
    );
    setAttachmentPreviewUrls(next);
    return () => {
      next.forEach((u) => {
        if (u) URL.revokeObjectURL(u);
      });
    };
  }, [attachments]);

  const isFileDragEvent = (e: React.DragEvent) => {
    const types = e.dataTransfer?.types;
    if (!types) return false;
    return Array.from(types as unknown as string[]).includes("Files");
  };

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

  const reorderAttachments = (fromIndex: number, toIndex: number) => {
    if (
      fromIndex === toIndex ||
      fromIndex < 0 ||
      toIndex < 0 ||
      fromIndex >= attachments.length ||
      toIndex >= attachments.length
    ) {
      return;
    }
    const next = [...attachments];
    const [item] = next.splice(fromIndex, 1);
    next.splice(toIndex, 0, item);
    onAttachmentsChange(next);
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (isLoading) return;
    const cd = e.clipboardData;
    if (!cd?.items?.length) return;
    const files: File[] = [];
    for (let i = 0; i < cd.items.length; i++) {
      const item = cd.items[i];
      if (item.kind === "file") {
        const f = item.getAsFile();
        if (f) files.push(f);
      }
    }
    if (files.length === 0) return;
    e.preventDefault();
    addFiles(files);
  };

  const attachmentOverBudget = attachmentTotalBytes > maxAttachmentTotalBytes;

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragDepth.current = 0;
    setIsFileDragging(false);
    if (isLoading) return;
    const dropped = Array.from(e.dataTransfer.files || []);
    addFiles(dropped);
  };

  const handleDragEnter = (e: React.DragEvent) => {
    if (isLoading || !isFileDragEvent(e)) return;
    e.preventDefault();
    dragDepth.current += 1;
    if (dragDepth.current === 1) setIsFileDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    if (isLoading) return;
    e.preventDefault();
    if (dragDepth.current === 0) return;
    dragDepth.current -= 1;
    if (dragDepth.current <= 0) {
      dragDepth.current = 0;
      setIsFileDragging(false);
    }
  };

  useEffect(() => {
    const clearDrag = () => {
      dragDepth.current = 0;
      setIsFileDragging(false);
      setDragOverTileIndex(null);
    };
    window.addEventListener("dragend", clearDrag);
    return () => window.removeEventListener("dragend", clearDrag);
  }, []);

  useEffect(() => {
    if (!isLoading) return;
    dragDepth.current = 0;
    setIsFileDragging(false);
  }, [isLoading]);

  const handleDragOver = (e: React.DragEvent) => {
    if (!isFileDragEvent(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-3 py-2 sm:px-4">
      <div
        className="relative"
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
      >
        {attachments.length > 0 ? (
          <div className="mb-2 flex flex-wrap gap-2 pl-1">
            {attachments.map((f, idx) => {
              const isImage = f.type.startsWith("image/");
              const preview = attachmentPreviewUrls[idx];
              const tileKey = `${f.name}-${f.size}-${f.lastModified}-${idx}`;
              return (
                <div
                  key={tileKey}
                  draggable={!isLoading}
                  onDragStart={(e) => {
                    e.dataTransfer.setData("text/plain", String(idx));
                    e.dataTransfer.effectAllowed = "move";
                  }}
                  onDragEnd={() => setDragOverTileIndex(null)}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = "move";
                    setDragOverTileIndex(idx);
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOverTileIndex(null);
                    const raw = e.dataTransfer.getData("text/plain");
                    const from = Number.parseInt(raw, 10);
                    if (Number.isNaN(from)) return;
                    reorderAttachments(from, idx);
                  }}
                  className={`relative flex h-14 w-[4.75rem] shrink-0 cursor-grab overflow-hidden rounded-xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-ghost)] shadow-sm active:cursor-grabbing sm:h-16 sm:w-[5.25rem] ${
                    dragOverTileIndex === idx
                      ? "ring-2 ring-fuchsia-400/70 ring-offset-2 ring-offset-transparent light:ring-violet-500/70"
                      : ""
                  }`}
                  title={`${f.name} — drag to reorder`}
                >
                  <div
                    className="flex w-4 shrink-0 flex-col items-center justify-center border-r border-[color:var(--c-border-soft)] bg-[var(--c-surface-field)] text-[var(--c-fg-hint)]"
                    aria-hidden
                  >
                    <GripVertical className="h-4 w-4 opacity-70" />
                  </div>
                  <div className="relative min-h-0 min-w-0 flex-1 self-stretch">
                    {isImage ? (
                      preview ? (
                        <img
                          src={preview}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-[var(--c-surface-field)]">
                          <div className="h-6 w-6 animate-pulse rounded-md bg-[var(--c-border-soft)]" />
                        </div>
                      )
                    ) : (
                      <div className="flex h-full w-full flex-col items-center justify-center gap-0.5 bg-[var(--c-surface-field)] p-0.5">
                        <FileText className="h-4 w-4 text-[var(--c-fg-hint)] sm:h-5 sm:w-5" aria-hidden />
                        <span className="w-full truncate px-0.5 text-center text-[8px] font-medium leading-tight text-[var(--c-fg-muted)]">
                          {(f.name || "file").replace(/\.[^.]+$/, "")}
                        </span>
                      </div>
                    )}
                    <button
                      type="button"
                      draggable={false}
                      onClick={(ev) => {
                        ev.stopPropagation();
                        onAttachmentsChange(attachments.filter((_, i) => i !== idx));
                      }}
                      disabled={isLoading}
                      className="absolute right-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-md border border-[color:var(--c-border-soft)] bg-black/55 text-white backdrop-blur-sm transition hover:bg-black/70 disabled:opacity-40 light:bg-black/40 light:hover:bg-black/55"
                      title="Remove attachment"
                    >
                      <X className="h-3 w-3" aria-hidden />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}

        <div
          className={debateComposerBar}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
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
            onPaste={handlePaste}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={onRun}
            disabled={!canRun}
            title={
              canRun
                ? "Run debate (Enter)"
                : attachmentOverBudget
                  ? `Attachments exceed ${formatMb(maxAttachmentTotalBytes)} MB total`
                  : "Add a question and at least one persona"
            }
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-fuchsia-500 to-purple-600 text-white shadow-lg shadow-purple-900/50 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40 light:shadow-violet-300/40"
          >
            {isLoading ? (
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            ) : (
              <Send className="h-5 w-5 translate-x-px" aria-hidden />
            )}
          </button>
        </div>

        {isFileDragging && !isLoading ? (
          <div
            className="absolute inset-0 z-[60] flex flex-col items-center justify-center gap-1 rounded-[2rem] border-2 border-dotted border-fuchsia-400/90 bg-[var(--c-surface-composer)]/90 text-center shadow-inner shadow-fuchsia-950/20 backdrop-blur-sm light:border-violet-500/85 light:bg-[var(--c-surface-field)]/92 light:shadow-violet-200/30"
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            role="presentation"
            aria-hidden={true}
          >
            <p className="px-4 text-sm font-bold uppercase tracking-[0.2em] text-fuchsia-100 light:text-violet-900">
              Drop your file here
            </p>
            <p className="px-4 text-[11px] font-medium text-purple-200/85 light:text-violet-700">
              Images, PDF, or Word — up to 8 files
            </p>
          </div>
        ) : null}
      </div>

      <p
        className={`mt-1.5 px-1 text-right text-[10px] tabular-nums ${
          attachmentOverBudget ? "font-medium text-rose-400 light:text-rose-600" : "text-[var(--c-fg-hint)]"
        }`}
      >
        Attachments: {formatMb(attachmentTotalBytes)} / {formatMb(maxAttachmentTotalBytes)} MB
        {attachmentOverBudget ? " — reduce size to run" : ""}
      </p>
    </div>
  );
};
