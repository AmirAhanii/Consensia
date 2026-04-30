import React, { useState } from "react";
import { MessageSquarePlus, Trash2, ChevronLeft, ChevronRight } from "lucide-react";

export type DebateSessionItem = {
  id: string;
  title: string;
  question: string;
  personas: object[];
  result: object | null;
  created_at: string;
  updated_at: string;
};

type Props = {
  sessions: DebateSessionItem[];
  currentSessionId: string | null;
  isLoggedIn: boolean;
  onSelect: (session: DebateSessionItem) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export const SessionSidebar: React.FC<Props> = ({
  sessions,
  currentSessionId,
  isLoggedIn,
  onSelect,
  onNew,
  onDelete,
}) => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`relative z-30 flex min-h-0 shrink-0 flex-col border-r border-[color:var(--c-border)] bg-[var(--c-surface-panel)] backdrop-blur transition-all duration-200 ${
        collapsed ? "w-10" : "w-60"
      }`}
    >
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="absolute -right-4 top-16 z-40 flex h-8 w-8 items-center justify-center rounded-full border border-[color:var(--c-border-strong)] bg-[var(--c-surface-chip)] text-[var(--c-fg-hint)] shadow-md shadow-black/20 transition-colors hover:bg-[var(--c-surface-chip-hover)] hover:text-[var(--c-fg)] light:text-[var(--c-fg)] light:shadow-[color:var(--c-shadow-card)] light:hover:bg-[var(--c-surface-chip-hover)]"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>

      {!collapsed && (
        <>
          <div className="border-b border-[color:var(--c-border)] p-3">
            <button
              type="button"
              onClick={onNew}
              className="flex w-full items-center gap-2 rounded-xl border border-[color:var(--c-border)] bg-purple-900/20 px-3 py-2 text-sm text-[var(--c-fg)] transition-colors hover:bg-purple-800/40 light:border-[color:var(--c-border-strong)] light:bg-[var(--c-surface-chip)] light:hover:bg-[var(--c-surface-chip-hover)]"
            >
              <MessageSquarePlus className="h-4 w-4 shrink-0" />
              New Debate
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-2">
            {!isLoggedIn ? (
              <p className="px-3 py-4 text-center text-xs leading-relaxed text-[var(--c-fg-hint)]">
                Log in to save and<br />
                switch between debates
              </p>
            ) : sessions.length === 0 ? (
              <p className="px-3 py-4 text-center text-xs text-[var(--c-fg-hint)]">
                No saved debates yet
              </p>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.id}
                  className={`group relative mx-2 mb-1 cursor-pointer rounded-xl px-3 py-2 transition-colors ${
                    s.id === currentSessionId
                      ? "border border-[color:var(--c-border-strong)] bg-purple-900/50 light:bg-[var(--c-surface-nav-active)]"
                      : "hover:bg-[var(--c-surface-nav-hover)]"
                  }`}
                  onClick={() => onSelect(s)}
                >
                  <p className="truncate pr-5 text-xs font-medium leading-snug text-[var(--c-fg)]">
                    {s.title}
                  </p>
                  <p className="mt-0.5 text-[10px] text-[var(--c-fg-hint)]">
                    {relativeTime(s.updated_at)}
                  </p>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(s.id);
                    }}
                    className="absolute right-2 top-2 hidden items-center justify-center rounded p-0.5 text-[var(--c-fg-hint)] transition-colors hover:text-rose-400 group-hover:flex light:hover:text-rose-600"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </aside>
  );
};
