import type { SessionInfo } from "../../types/api";

interface SessionListProps {
  sessions: SessionInfo[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  collapsed: boolean;
  onToggle: () => void;
}

export function SessionList({
  sessions,
  activeSessionId,
  onSelect,
  onCreate,
  onDelete,
  collapsed,
  onToggle,
}: SessionListProps) {
  if (collapsed) {
    return (
      <div className="w-12 bg-[var(--bg-surface)] border-r border-[var(--border-dim)] flex flex-col items-center py-4 gap-4">
        <button
          onClick={onToggle}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--text-lo)] hover:text-[var(--text-mid)] hover:bg-[var(--bg-elevated)] transition-colors"
          title="Expand sidebar"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="4" width="12" height="1.5" rx="0.75" fill="currentColor" />
            <rect x="2" y="7.25" width="12" height="1.5" rx="0.75" fill="currentColor" />
            <rect x="2" y="10.5" width="12" height="1.5" rx="0.75" fill="currentColor" />
          </svg>
        </button>
        <button
          onClick={onCreate}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--text-lo)] hover:text-[var(--accent)] hover:bg-[var(--accent-dim)] transition-colors"
          title="New Chat"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="w-64 bg-[var(--bg-surface)] border-r border-[var(--border-dim)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-[var(--border-dim)]">
        <span
          className="text-sm font-semibold text-[var(--text-hi)] tracking-wide"
          style={{ fontFamily: "Syne, sans-serif" }}
        >
          Chats
        </span>
        <button
          onClick={onToggle}
          className="w-6 h-6 flex items-center justify-center text-[var(--text-lo)] hover:text-[var(--text-mid)] transition-colors"
          title="Collapse sidebar"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M9 2L5 7l4 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {/* New chat button */}
      <div className="px-3 py-3 border-b border-[var(--border-dim)]">
        <button
          onClick={onCreate}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-[var(--text-mid)] border border-[var(--border-mid)] hover:border-[var(--accent)] hover:text-[var(--accent)] hover:bg-[var(--accent-dim)] transition-all duration-150"
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M6.5 1.5v10M1.5 6.5h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <span>New chat</span>
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto py-2">
        {sessions.length === 0 && (
          <p className="text-xs text-[var(--text-lo)] text-center mt-6 px-4">
            No conversations yet
          </p>
        )}
        {sessions.map((session) => {
          const isActive = activeSessionId === session.session_id;
          return (
            <div
              key={session.session_id}
              className={`group flex items-center gap-2 mx-2 my-0.5 px-3 py-2 rounded-lg cursor-pointer transition-all duration-150 ${
                isActive
                  ? "bg-[var(--bg-elevated)] border border-[var(--border-mid)]"
                  : "hover:bg-[var(--bg-elevated)]/50"
              }`}
            >
              {isActive && (
                <span
                  className="w-1 h-1 rounded-full flex-shrink-0"
                  style={{ background: "var(--accent)" }}
                />
              )}
              <span
                className={`flex-1 truncate text-sm ${
                  isActive ? "text-[var(--text-hi)]" : "text-[var(--text-mid)]"
                }`}
                onClick={() => onSelect(session.session_id)}
              >
                {session.title}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(session.session_id);
                }}
                className="flex-shrink-0 w-5 h-5 flex items-center justify-center text-[var(--text-lo)] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all duration-150"
              >
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path d="M2 2l6 6M8 2L2 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
