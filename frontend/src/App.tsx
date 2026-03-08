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

  // Send pending message once a session becomes active
  useEffect(() => {
    if (activeSessionId && pendingMessageRef.current) {
      const msg = pendingMessageRef.current;
      pendingMessageRef.current = null;
      send(msg);
    }
  }, [activeSessionId, send]);

  const handleNewChat = async () => {
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

  return (
    <div className="flex h-screen bg-gray-50">
      <SessionList
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onCreate={handleNewChat}
        onDelete={removeSession}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div className="flex-1 flex flex-col">
        <header className="flex items-center justify-between px-4 py-2 bg-white border-b">
          <h1 className="font-semibold text-gray-800">Census Chat Agent</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{username}</span>
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-red-600"
            >
              Logout
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
      <div className="flex items-center justify-center h-screen">
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
