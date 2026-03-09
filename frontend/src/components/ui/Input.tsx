import type { InputHTMLAttributes } from "react";

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full px-3 py-2.5 bg-[var(--bg-elevated)] border border-[var(--border-mid)] rounded-lg text-[var(--text-hi)] placeholder:text-[var(--text-lo)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-dim)] transition-colors duration-150 ${className}`}
      {...props}
    />
  );
}
