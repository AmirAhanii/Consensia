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
      className={`relative flex-shrink-0 flex flex-col border-r border-purple-900/40 bg-black/50 backdrop-blur transition-all duration-200 ${
        collapsed ? "w-10" : "w-60"
      }`}
    >
      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="absolute -right-3 top-6 z-20 flex h-6 w-6 items-center justify-center rounded-full border border-purple-800/60 bg-black text-purple-400 hover:text-white transition-colors"
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>

      {!collapsed && (
        <>
          {/* New debate button */}
          <div className="p-3 border-b border-purple-900/40">
            <button
              onClick={onNew}
              className="flex w-full items-center gap-2 rounded-xl border border-purple-800/50 bg-purple-900/20 px-3 py-2 text-sm text-purple-100 hover:bg-purple-800/40 transition-colors"
            >
              <MessageSquarePlus className="w-4 h-4 shrink-0" />
              New Debate
            </button>
          </div>

          {/* Session list */}
          <div className="flex-1 overflow-y-auto py-2">
            {!isLoggedIn ? (
              <p className="px-3 py-4 text-xs text-purple-500 text-center leading-relaxed">
                Log in to save and<br />switch between debates
              </p>
            ) : sessions.length === 0 ? (
              <p className="px-3 py-4 text-xs text-purple-500 text-center">
                No saved debates yet
              </p>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.id}
                  className={`group relative mx-2 mb-1 rounded-xl px-3 py-2 cursor-pointer transition-colors ${
                    s.id === currentSessionId
                      ? "bg-purple-900/50 border border-purple-700/50"
                      : "hover:bg-purple-900/30"
                  }`}
                  onClick={() => onSelect(s)}
                >
                  <p className="text-xs font-medium text-purple-100 truncate pr-5 leading-snug">
                    {s.title}
                  </p>
                  <p className="text-[10px] text-purple-500 mt-0.5">
                    {relativeTime(s.updated_at)}
                  </p>
                  <button
                    onClick={(e) => { e.stopPropagation(); onDelete(s.id); }}
                    className="absolute right-2 top-2 hidden group-hover:flex items-center justify-center rounded p-0.5 text-purple-500 hover:text-rose-400 transition-colors"
                  >
                    <Trash2 className="w-3 h-3" />
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
