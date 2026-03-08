import { useCallback, useEffect, useState } from "react";
import type { SessionInfo } from "../types/api";
import {
  createSession as apiCreateSession,
  deleteSession as apiDeleteSession,
  listSessions,
} from "../services/api";

export function useSession(isLoggedIn: boolean) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadSessions = useCallback(async () => {
    if (!isLoggedIn) return;
    setIsLoading(true);
    try {
      const list = await listSessions();
      setSessions(list);
    } finally {
      setIsLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const createSession = useCallback(async (title?: string) => {
    const session = await apiCreateSession(title);
    setSessions((prev) => [session, ...prev]);
    setActiveSessionId(session.session_id);
    return session;
  }, []);

  const removeSession = useCallback(
    async (sessionId: string) => {
      await apiDeleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
    },
    [activeSessionId]
  );

  const renameSession = useCallback((sessionId: string, title: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.session_id === sessionId ? { ...s, title } : s))
    );
  }, []);

  return {
    sessions,
    activeSessionId,
    setActiveSessionId,
    createSession,
    removeSession,
    renameSession,
    isLoading,
    reload: loadSessions,
  };
}
