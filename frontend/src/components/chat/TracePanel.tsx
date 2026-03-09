import { useState } from "react";
import type { ReactNode } from "react";
import type { TraceData, TraceIteration } from "../../types/ui";

interface TracePanelProps {
  trace: TraceData;
}

function CodeBlock({ code }: { code: string }) {
  return (
    <pre
      className="text-xs rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-48 border border-[var(--border-dim)] leading-relaxed"
      style={{
        background: "var(--bg-base)",
        color: "var(--cyan)",
        fontFamily: "JetBrains Mono, monospace",
      }}
    >
      {code}
    </pre>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-4">
      <h4
        className="text-xs font-semibold uppercase tracking-widest mb-2 flex items-center gap-2"
        style={{ color: "var(--text-lo)" }}
      >
        <span
          className="w-1 h-1 rounded-full inline-block"
          style={{ background: "var(--accent)" }}
        />
        {title}
      </h4>
      {children}
    </div>
  );
}

function FipsSection({ iterations }: { iterations: TraceIteration[] }) {
  const items = iterations.filter((i) => i.tool === "search_fips_codes");
  if (items.length === 0) return null;
  return (
    <Section title="FIPS Resolution">
      {items.map((iter, i) => (
        <div key={i} className="mb-2">
          <p className="text-xs mb-1" style={{ color: "var(--text-lo)" }}>
            Query:{" "}
            <span style={{ color: "var(--text-mid)", fontFamily: "JetBrains Mono, monospace" }}>
              {JSON.stringify(iter.tool_input)}
            </span>
          </p>
          <CodeBlock code={iter.tool_result ?? "(no result)"} />
        </div>
      ))}
    </Section>
  );
}

function FeatureSearchSection({ iterations }: { iterations: TraceIteration[] }) {
  const items = iterations.filter((i) => i.tool === "search_feature_schema");
  if (items.length === 0) return null;
  return (
    <Section title="Feature Search">
      {items.map((iter, i) => (
        <div key={i} className="mb-2">
          <p className="text-xs mb-1" style={{ color: "var(--text-lo)" }}>
            Query:{" "}
            <span style={{ color: "var(--text-mid)", fontFamily: "JetBrains Mono, monospace" }}>
              {JSON.stringify(iter.tool_input)}
            </span>
          </p>
          <CodeBlock code={iter.tool_result ?? "(no result)"} />
        </div>
      ))}
    </Section>
  );
}

function FieldDescSection({ iterations }: { iterations: TraceIteration[] }) {
  const items = iterations.filter((i) => i.tool === "get_field_descriptions");
  if (items.length === 0) return null;
  return (
    <Section title="Field Descriptions">
      {items.map((iter, i) => (
        <div key={i} className="mb-2">
          <p className="text-xs mb-1" style={{ color: "var(--text-lo)" }}>
            Table:{" "}
            <span style={{ color: "var(--text-mid)", fontFamily: "JetBrains Mono, monospace" }}>
              {JSON.stringify(iter.tool_input)}
            </span>
          </p>
          <CodeBlock code={iter.tool_result ?? "(no result)"} />
        </div>
      ))}
    </Section>
  );
}

function SqlSection({ iterations }: { iterations: TraceIteration[] }) {
  const items = iterations.filter((i) => i.tool === "execute_sql");
  if (items.length === 0) return null;
  return (
    <Section title="SQL Query">
      {items.map((iter, i) => (
        <div key={i} className="mb-3">
          <p className="text-xs mb-1" style={{ color: "var(--text-lo)" }}>Query:</p>
          <CodeBlock
            code={
              typeof iter.tool_input?.sql === "string"
                ? iter.tool_input.sql
                : JSON.stringify(iter.tool_input) ?? ""
            }
          />
          <p className="text-xs mt-2 mb-1" style={{ color: "var(--text-lo)" }}>Result:</p>
          <CodeBlock code={iter.tool_result ?? "(no result)"} />
        </div>
      ))}
    </Section>
  );
}

function ReasoningSection({ iterations }: { iterations: TraceIteration[] }) {
  const items = iterations.filter((i) => i.thinking?.trim());
  if (items.length === 0) return null;
  return (
    <Section title="Reasoning">
      {items.map((iter) => (
        <div key={iter.iteration} className="mb-2">
          <p className="text-xs mb-0.5" style={{ color: "var(--text-lo)" }}>
            Step {iter.iteration + 1}
          </p>
          <p
            className="text-xs italic whitespace-pre-wrap leading-relaxed"
            style={{ color: "var(--text-mid)" }}
          >
            {iter.thinking}
          </p>
        </div>
      ))}
    </Section>
  );
}

export function TracePanel({ trace }: TracePanelProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-4 pt-3 border-t border-[var(--border-dim)]">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs transition-colors duration-150 group"
        style={{ color: "var(--text-lo)" }}
      >
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="none"
          className="transition-transform duration-150"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          <path d="M3 2l4 3-4 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span
          className="group-hover:text-[var(--text-mid)] transition-colors"
          style={{ fontFamily: "JetBrains Mono, monospace" }}
        >
          {open ? "hide trace" : "view trace"}
        </span>
      </button>

      {open && (
        <div
          className="mt-3 rounded-xl border border-[var(--border-dim)] p-4"
          style={{ background: "var(--bg-surface)" }}
        >
          <FipsSection iterations={trace.iterations} />
          <FeatureSearchSection iterations={trace.iterations} />
          <FieldDescSection iterations={trace.iterations} />
          <SqlSection iterations={trace.iterations} />
          <ReasoningSection iterations={trace.iterations} />
        </div>
      )}
    </div>
  );
}
