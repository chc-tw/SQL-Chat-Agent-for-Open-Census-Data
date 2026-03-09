import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonProps) {
  const base =
    "px-4 py-2 rounded-lg font-medium text-sm transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed";
  const variants = {
    primary:
      "bg-[var(--accent)] text-white hover:brightness-110 active:brightness-95 shadow-[0_0_16px_var(--accent-dim)]",
    secondary:
      "bg-[var(--bg-elevated)] text-[var(--text-mid)] border border-[var(--border-mid)] hover:border-[var(--border-lit)] hover:text-[var(--text-hi)]",
    danger:
      "bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 hover:border-red-500/40",
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${className}`}
      {...props}
    />
  );
}
