import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { login as apiLogin, getMe } from "../services/api";

interface AuthState {
  username: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthState>({
  username: null,
  isLoading: true,
  login: async () => {},
  logout: () => {},
});

export function useAuthProvider(): AuthState {
  const [username, setUsername] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    getMe()
      .then((user) => setUsername(user.username))
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (user: string, password: string) => {
    const res = await apiLogin({ username: user, password });
    localStorage.setItem("token", res.access_token);
    setUsername(user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setUsername(null);
  }, []);

  return { username, isLoading, login, logout };
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
