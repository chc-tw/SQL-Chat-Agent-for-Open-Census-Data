import { useEffect, useRef, useState } from "react";
import { AuthContext, useAuth, useAuthProvider } from "./hooks/useAuth";
import { useSession } from "./hooks/useSession";
import { useChat } from "./hooks/useChat";
import { LoginForm } from "./components/auth/LoginForm";
import { SessionList } from "./components/chat/SessionList";
import { ChatWindow } from "./components/chat/ChatWindow";
import { Spinner } from "./components/ui/Spinner";

function ChatApp() {
  const { username, logout } = useAuth();
  const {
    sessions,
    activeSessionId,
    setActiveSessionId,
    createSession,
    removeSession,
    renameSession,
  } = useSession(!!username);
  const { messages, isStreaming, send } = useChat(activeSessionId, renameSession);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const pendingMessageRef = useRef<string | null>(null);

  useEffect(() => {
    if (activeSessionId && pendingMessageRef.current) {
      const msg = pendingMessageRef.current;
      pendingMessageRef.current = null;
      send(msg);
    }
  }, [activeSessionId, send]);

  const handleNewChat = async () => {
    // Only create a new session if the current one already has messages
    if (activeSessionId && messages.length === 0) return;
    await createSession();
  };

  const handleSend = async (content: string) => {
    if (!activeSessionId) {
      pendingMessageRef.current = content;
      await createSession();
      return;
    }
    send(content);
  };

  const userInitial = username?.[0]?.toUpperCase() ?? "?";

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-base)" }}>
      <SessionList
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onCreate={handleNewChat}
        onDelete={removeSession}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header
          className="flex items-center justify-between px-5 py-3 border-b border-[var(--border-dim)] flex-shrink-0"
          style={{ background: "var(--bg-surface)" }}
        >
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div
                className="w-6 h-6 rounded-md flex items-center justify-center"
                style={{ background: "var(--accent)" }}
              >
                <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                  <circle cx="5.5" cy="5.5" r="2" fill="white" />
                  <path d="M5.5 1v2M5.5 8v2M1 5.5h2M8 5.5h2" stroke="white" strokeWidth="1.2" strokeLinecap="round" />
                </svg>
              </div>
              <span
                className="text-sm font-bold text-[var(--text-hi)] tracking-wide"
                style={{ fontFamily: "Syne, sans-serif" }}
              >
                Census AI
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--border-dim)]"
              style={{ background: "var(--bg-elevated)" }}
            >
              <div
                className="w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-semibold"
                style={{ background: "var(--accent)", fontFamily: "Syne, sans-serif" }}
              >
                {userInitial}
              </div>
              <span className="text-xs text-[var(--text-mid)]">{username}</span>
            </div>
            <button
              onClick={logout}
              className="text-xs text-[var(--text-lo)] hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-red-500/10"
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-hidden">
          <ChatWindow
            messages={messages}
            isStreaming={isStreaming}
            onSend={handleSend}
          />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const auth = useAuthProvider();

  if (auth.isLoading) {
    return (
      <div
        className="flex items-center justify-center h-screen"
        style={{ background: "var(--bg-base)" }}
      >
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <AuthContext value={auth}>
      {auth.username ? <ChatApp /> : <LoginForm />}
    </AuthContext>
  );
}
