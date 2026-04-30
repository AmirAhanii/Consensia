import React, { useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { debateComposerBar, debateComposerTextarea } from "../theme/themeClasses";

type Props = {
  question: string;
  onChange: (value: string) => void;
  onRun: () => void;
  canRun: boolean;
  isLoading: boolean;
};

export const DebateComposer: React.FC<Props> = ({
  question,
  onChange,
  onRun,
  canRun,
  isLoading,
}) => {
  const taRef = useRef<HTMLTextAreaElement>(null);

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

  return (
    <div className="mx-auto w-full max-w-3xl px-3 py-2 sm:px-4">
      <div className={debateComposerBar}>
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
