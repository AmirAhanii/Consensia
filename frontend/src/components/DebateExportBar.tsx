import React from "react";
import { FileDown, Printer } from "lucide-react";
import { toast } from "react-toastify";
import type { DebateMessage, DebateResult, Persona } from "../types";
import {
  buildDebateMarkdown,
  downloadTextFile,
  printDebateExport,
  slugFromQuestion,
  type DebateExportAttachmentMeta,
} from "../utils/debateExport";

type Props = {
  question: string;
  personas: Persona[];
  attachments: DebateExportAttachmentMeta[];
  result: DebateResult;
  messages?: DebateMessage[] | null;
};

export const DebateExportBar: React.FC<Props> = ({
  question,
  personas,
  attachments,
  result,
  messages,
}) => {
  const buildInput = () => ({
    exportedAtIso: new Date().toISOString(),
    question,
    personas,
    attachments,
    result,
    messages,
  });

  const handleMarkdown = () => {
    const md = buildDebateMarkdown(buildInput());
    const slug = slugFromQuestion(question);
    const stamp = new Date().toISOString().slice(0, 10);

    downloadTextFile(`consensia-${slug}-${stamp}.md`, md, "text/markdown;charset=utf-8");
    toast.success("Markdown downloaded.");
  };

  const handlePdf = () => {
    try {
      const opened = printDebateExport(buildInput());

      if (!opened) {
        toast.error("Could not open print dialog.");
        return;
      }

      toast.info("Use your browser’s print dialog → Save as PDF.");
    } catch {
      toast.error("Could not open print dialog.");
    }
  };

  return (
    <div className="mb-3 flex flex-wrap items-center justify-end gap-2">
      <button
        type="button"
        onClick={handleMarkdown}
        className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--c-border-soft)] bg-[var(--c-surface-chip)] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--c-fg)] transition hover:border-[color:var(--c-border-strong)] hover:bg-[var(--c-surface-chip-hover)]"
      >
        <FileDown className="h-3.5 w-3.5" aria-hidden />
        Markdown
      </button>

      <button
        type="button"
        onClick={handlePdf}
        className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--c-border-soft)] bg-[var(--c-surface-chip)] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--c-fg)] transition hover:border-[color:var(--c-border-strong)] hover:bg-[var(--c-surface-chip-hover)]"
      >
        <Printer className="h-3.5 w-3.5" aria-hidden />
        PDF (print)
      </button>
    </div>
  );
};
