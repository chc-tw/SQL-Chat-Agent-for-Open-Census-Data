import { useState } from "react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { useAuth } from "../../hooks/useAuth";

export function LoginForm() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await login(username, password);
    } catch {
      setError("Invalid username or password");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-[var(--bg-base)] relative overflow-hidden"
    >
      {/* Ambient glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 50% 40%, var(--accent-glow) 0%, transparent 70%)",
        }}
      />
      {/* Dot grid */}
      <div
        className="absolute inset-0 pointer-events-none opacity-30"
        style={{
          backgroundImage:
            "radial-gradient(circle, var(--border-mid) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />

      <div className="relative w-full max-w-sm mx-4">
        {/* Logo mark */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-3">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: "var(--accent)" }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="3" fill="white" />
                <path d="M8 2v2M8 12v2M2 8h2M12 8h2" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
            <span
              className="text-xl font-bold text-[var(--text-hi)]"
              style={{ fontFamily: "Syne, sans-serif" }}
            >
              Census AI
            </span>
          </div>
          <p className="text-sm text-[var(--text-lo)]">
            US Open Census Data · Powered by Snowflake
          </p>
        </div>

        {/* Card */}
        <div
          className="bg-[var(--bg-surface)] border border-[var(--border-mid)] rounded-2xl p-8"
          style={{ boxShadow: "0 0 40px var(--accent-glow)" }}
        >
          <h2
            className="text-lg font-semibold text-[var(--text-hi)] mb-6"
            style={{ fontFamily: "Syne, sans-serif" }}
          >
            Sign in to continue
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[var(--text-lo)] uppercase tracking-wider mb-1.5">
                Username
              </label>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-lo)] uppercase tracking-wider mb-1.5">
                Password
              </label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
                <span className="text-red-400 text-xs">{error}</span>
              </div>
            )}

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 mt-2"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-pulse">Signing in</span>
                  <span className="flex gap-1">
                    <span className="thinking-dot w-1 h-1 rounded-full bg-white inline-block" />
                    <span className="thinking-dot w-1 h-1 rounded-full bg-white inline-block" />
                    <span className="thinking-dot w-1 h-1 rounded-full bg-white inline-block" />
                  </span>
                </span>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
