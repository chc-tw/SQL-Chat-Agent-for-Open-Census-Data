import { useState } from "react";

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="px-6 pb-4 pt-3" style={{ background: "var(--bg-base)" }}>
      <form
        onSubmit={handleSubmit}
        className="mx-auto max-w-3xl"
      >
        <div
          className="flex items-center border border-[var(--border-mid)] rounded-3xl px-5 py-4 focus-within:border-[var(--border-lit)] transition-colors duration-150"
          style={{
            background: "var(--bg-surface)",
            boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
          }}
        >
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about US Census data…"
            disabled={disabled}
            rows={1}
            autoFocus
            className="flex-1 bg-transparent text-[var(--text-hi)] placeholder:text-[var(--text-lo)] text-sm resize-none focus:outline-none disabled:opacity-40 leading-relaxed"
            style={{ minHeight: "24px", maxHeight: "160px" }}
            onInput={(e) => {
              const target = e.currentTarget;
              target.style.height = "auto";
              target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
            }}
          />
        </div>
      </form>
      <p className="text-center text-[var(--text-lo)] text-xs mt-2">
        Enter ↵ to send · Shift + Enter for new line
      </p>
    </div>
  );
}
