import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertTriangle, BookOpen, Check, ChevronDown, Copy, HelpCircle, Ban, RotateCw, Wifi } from "lucide-react";
import type { AskResponse, NumericalResponse, TheoryResponse } from "@/types/api";
import { GanttChart } from "@/components/Numerical/GanttChart";
import { ProcessTable, ResultTable, SolutionSummary } from "@/components/Numerical/Tables";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { Button } from "@/components/ui/button";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{title}</h4>
      {children}
    </section>
  );
}

export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-tutor text-[15px]">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}

export function TheoryResponseView({ r }: { r: TheoryResponse; onFollowUp?: ((t: string) => void) | undefined }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  return (
    <div className="space-y-4">
      {r.topic && (
        <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-0.5 text-xs">
          <span className="text-muted-foreground">Topic:</span> {r.topic}
        </span>
      )}
      <Markdown>{r.answer}</Markdown>
      {r.sources && r.sources.length > 0 && (
        <Section title="Course Material">
          <ul className="space-y-1 text-sm">
            {r.sources.map((s, i) => (
              <li key={i} className="flex items-start gap-2">
                <BookOpen className="mt-0.5 size-3.5 text-primary" aria-hidden />
                <span>
                  {[s.title ?? s.source, s.module && `Module ${s.module}`, s.page !== undefined && `Page ${s.page}`].filter(Boolean).join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      <div className="flex gap-2">
        <Button
          variant="ghost" size="sm"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(r.answer);
              setCopied(true); setCopyError(false);
              setTimeout(() => setCopied(false), 1500);
            } catch { setCopyError(true); }
          }}
        >
          {copied ? <Check /> : <Copy />} {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      {copyError && <p className="text-xs text-destructive" role="alert">Couldn't copy. Please select the answer and copy it manually.</p>}
    </div>
  );
}

export function NumericalResponseView({ r }: { r: NumericalResponse }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-display text-base font-semibold">Numerical Solution</span>
        <span className="rounded-md bg-accent px-2 py-0.5 font-mono text-xs text-accent-foreground">{r.algorithm}</span>
        {r.input.time_quantum !== undefined && (
          <span className="rounded-md border border-border px-2 py-0.5 font-mono text-xs">Time Quantum: {r.input.time_quantum}</span>
        )}
      </div>
      <Section title="Input Data"><ProcessTable processes={r.input.processes} /></Section>
      <Section title="Gantt Chart"><GanttChart blocks={r.gantt_chart} /></Section>
      <Section title="Process Calculations"><ResultTable results={r.process_results} /></Section>
      <SolutionSummary awt={r.average_waiting_time} atat={r.average_turnaround_time} />
      {r.explanation && (
        <section className="rounded-lg border border-border">
          <Button variant="ghost"
            className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            How it was solved
            <ChevronDown className={`size-4 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />
          </Button>
          {open && <div className="border-t border-border px-4 py-2"><Markdown>{r.explanation}</Markdown></div>}
        </section>
      )}
    </div>
  );
}

export function NeedsInputView({ message }: { message: string }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 font-medium"><HelpCircle className="size-4 text-primary" aria-hidden /> I can solve this, but I need a few details first.</div>
      {message && <p className="text-sm text-muted-foreground">{message}</p>}
      <div className="grid gap-2 sm:grid-cols-3">
        {[
          ["Process format", "P1(0,5)\nP2(1,3)\nP3(2,8)"],
          ["Priority", "P1(0,5,2)\nP2(1,3,1)"],
          ["Round Robin", "Time Quantum: 3"],
        ].map(([t, c]) => (
          <div key={t} className="rounded-md border border-border bg-surface-2 p-3">
            <div className="mb-1 text-xs text-muted-foreground">{t}</div>
            <pre className="font-mono text-xs whitespace-pre-wrap">{c}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}

export function UnsupportedView({ message }: { message: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 font-medium"><Ban className="size-4 text-primary" aria-hidden /> Currently unsupported</div>
      {message && <p className="text-sm text-muted-foreground">{message}</p>}
    </div>
  );
}

export function ErrorView({ message, connection, onRetry }: { message: string; connection?: boolean | undefined; onRetry?: (() => void) | undefined }) {
  const { recheck, status } = useBackendHealth();
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 font-medium text-destructive">
        {connection ? <Wifi className="size-4" aria-hidden /> : <AlertTriangle className="size-4" aria-hidden />}
        {connection ? "The tutor is temporarily unreachable" : "Couldn't complete your request"}
      </div>
      <p className="text-sm text-muted-foreground">{connection ? "The free service may be waking up. Wait a moment, then check the connection or retry your question." : message}</p>
      <div className="flex flex-wrap gap-2">
        {onRetry && <Button size="sm" variant="secondary" onClick={onRetry}><RotateCw /> Retry</Button>}
        {connection && (
          <Button size="sm" variant="ghost" disabled={status === "checking"} onClick={() => void recheck()}>
            Check Connection {status !== "checking" && <span className="text-muted-foreground">({status === "connected" ? "connected" : status === "starting" ? "starting" : "unavailable"})</span>}
          </Button>
        )}
      </div>
    </div>
  );
}

export function ResponseView({ r, onFollowUp, onRetry }: { r: AskResponse; onFollowUp?: ((t: string) => void) | undefined; onRetry?: (() => void) | undefined }) {
  switch (r.type) {
    case "theory": return <TheoryResponseView r={r} onFollowUp={onFollowUp} />;
    case "numerical": return <NumericalResponseView r={r} />;
    case "needs_input": return <NeedsInputView message={r.message} />;
    case "unsupported": return <UnsupportedView message={r.message} />;
    case "error": return <ErrorView message={r.message} connection={r.connection} onRetry={onRetry} />;
    default: return <ErrorView message="Unrecognised response." />;
  }
}
