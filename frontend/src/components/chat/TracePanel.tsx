import { useState } from "react";
import type { ReactNode } from "react";
import type { TraceData, TraceIteration } from "../../types/ui";

interface TracePanelProps {
  trace: TraceData;
}

function CodeBlock({ code }: { code: string }) {
  return (
    <pre className="text-xs bg-gray-50 border border-gray-200 rounded p-2 overflow-x-auto whitespace-pre-wrap break-words max-h-48">
      {code}
    </pre>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
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
          <p className="text-xs text-gray-500 mb-1">
            Query:{" "}
            <span className="font-mono text-gray-700">
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
          <p className="text-xs text-gray-500 mb-1">
            Query:{" "}
            <span className="font-mono text-gray-700">
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
          <p className="text-xs text-gray-500 mb-1">
            Table:{" "}
            <span className="font-mono text-gray-700">
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
          <p className="text-xs text-gray-400 mb-1">Query:</p>
          <CodeBlock
            code={
              typeof iter.tool_input?.sql === "string"
                ? iter.tool_input.sql
                : JSON.stringify(iter.tool_input) ?? ""
            }
          />
          <p className="text-xs text-gray-400 mt-2 mb-1">Result:</p>
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
          <p className="text-xs text-gray-400 mb-0.5">Step {iter.iteration + 1}</p>
          <p className="text-xs italic text-gray-600 whitespace-pre-wrap leading-relaxed">
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
    <div className="mt-3 pt-2 border-t border-gray-100">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        {open ? "Hide Trace ▲" : "View Trace ▼"}
      </button>
      {open && (
        <div className="mt-3">
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
