import { createFileRoute } from "@tanstack/react-router";
import { Loader2, Plus, RotateCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Container, Footer, PageHeader } from "@/components/Layout/Page";
import { ResponseView } from "@/components/Responses/Responses";
import { ask } from "@/services/api";
import type { AskResponse } from "@/types/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/numerical")({
  head: () => ({
    meta: [
      { title: "Numerical Lab — OS Tutor" },
      { name: "description", content: "Enter processes and solve FCFS, SJF, Priority and Round Robin scheduling with exact Gantt charts and step-by-step working." },
      { property: "og:title", content: "Numerical Lab — OS Tutor" },
      { property: "og:description", content: "An interactive CPU scheduling lab with exact results." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: NumericalLab,
});

const ALGOS = [
  { id: "FCFS", label: "FCFS" },
  { id: "SJF", label: "SJF (non-preemptive)" },
  { id: "Priority", label: "Priority" },
  { id: "Round Robin", label: "Round Robin" },
] as const;
type Algo = (typeof ALGOS)[number]["id"];

interface Row { at: string; bt: string; pr: string }
const blank = (): Row[] => [{ at: "0", bt: "", pr: "" }, { at: "", bt: "", pr: "" }, { at: "", bt: "", pr: "" }];

const isInt = (s: string) => /^\d+$/.test(s.trim());

function NumericalLab() {
  const [algo, setAlgo] = useState<Algo>("FCFS");
  const [rows, setRows] = useState<Row[]>(blank);
  const [quantum, setQuantum] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);

  const needsPr = algo === "Priority";
  const needsQ = algo === "Round Robin";

  const update = (i: number, k: keyof Row, v: string) => { setResult(null); setErrors([]); setRows((r) => r.map((row, j) => (j === i ? { ...row, [k]: v } : row))); };

  const buildQuestion = () => {
    const errs: string[] = [];
    rows.forEach((r, i) => {
      if (!isInt(r.at)) errs.push(`P${i + 1}: arrival time must be a whole number.`);
      if (!isInt(r.bt) || Number(r.bt) === 0) errs.push(`P${i + 1}: burst time must be a positive whole number.`);
      if (needsPr && !isInt(r.pr)) errs.push(`P${i + 1}: priority is required.`);
    });
    if (needsQ && (!isInt(quantum) || Number(quantum) === 0)) errs.push("Time quantum must be a positive whole number.");
    if (!rows.length) errs.push("Add at least one process.");
    setErrors(errs);
    if (errs.length) return null;
    const procs = rows.map((r, i) => `P${i + 1}(${r.at.trim()},${r.bt.trim()}${needsPr ? `,${r.pr.trim()}` : ""})`).join(", ");
    if (algo === "Round Robin") return `Solve Round Robin with time quantum ${quantum.trim()} for ${procs}`;
    if (algo === "Priority") return `Solve non-preemptive Priority scheduling for ${procs}`;
    if (algo === "SJF") return `Solve non-preemptive SJF scheduling for ${procs}`;
    return `Solve FCFS scheduling for ${procs}`;
  };

  const solve = async () => {
    if (loading) return;
    const q = buildQuestion();
    if (!q) return;
    setLoading(true);
    setResult(null);
    setResult(await ask(q));
    setLoading(false);
  };

  const reset = () => { setRows(blank()); setQuantum(""); setErrors([]); setResult(null); };
  const inputCls = "h-9 w-full rounded-md border border-input bg-background px-2 font-mono text-sm";

  return (
    <>
      <Container>
        <PageHeader eyebrow="Numerical Lab" title="CPU Scheduling Lab" subtitle="Enter your processes and let the solver compute exact completion, turnaround and waiting times." />

        <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
          <fieldset disabled={loading} className="card-surface min-w-0 h-fit p-5" aria-label="Problem input">
            <fieldset>
              <legend className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Algorithm</legend>
              <div className="grid grid-cols-2 gap-1.5" role="radiogroup">
                {ALGOS.map((a) => (
                   <Button variant="outline"
                    key={a.id}
                    role="radio"
                    aria-checked={algo === a.id}
                    onClick={() => { setAlgo(a.id); setResult(null); }}
                    className={cn("h-auto min-h-10 justify-start whitespace-normal px-3 py-2 text-left text-sm", algo === a.id ? "border-primary bg-accent text-accent-foreground" : "border-border hover:border-primary/40")}
                  >
                    {a.label}
                  </Button>
                ))}
              </div>
            </fieldset>

            {needsQ && (
              <label className="mt-5 block">
                <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-muted-foreground">Time Quantum</span>
                <input inputMode="numeric" value={quantum} onChange={(e) => { setQuantum(e.target.value); setResult(null); }} className={inputCls} placeholder="e.g. 3" />
              </label>
            )}

            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">Processes</caption>
                <thead className="text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="py-1 pr-2 font-medium">Process</th>
                    <th className="py-1 pr-2 font-medium">Arrival</th>
                    <th className="py-1 pr-2 font-medium">Burst</th>
                    {needsPr && <th className="py-1 pr-2 font-medium">Priority</th>}
                    <th><span className="sr-only">Remove</span></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i}>
                      <td className="py-1 pr-2 font-mono font-semibold">P{i + 1}</td>
                      <td className="py-1 pr-2"><input aria-label={`P${i + 1} arrival time`} inputMode="numeric" value={r.at} onChange={(e) => update(i, "at", e.target.value)} className={inputCls} /></td>
                      <td className="py-1 pr-2"><input aria-label={`P${i + 1} burst time`} inputMode="numeric" value={r.bt} onChange={(e) => update(i, "bt", e.target.value)} className={inputCls} /></td>
                      {needsPr && <td className="py-1 pr-2"><input aria-label={`P${i + 1} priority`} inputMode="numeric" value={r.pr} onChange={(e) => update(i, "pr", e.target.value)} className={inputCls} /></td>}
                      <td className="py-1">
                        <Button variant="ghost" size="icon" onClick={() => { setResult(null); setRows((rs) => rs.filter((_, j) => j !== i)); }} disabled={rows.length <= 1} aria-label={`Remove P${i + 1}`} className="size-8 text-muted-foreground hover:text-destructive">
                          <Trash2 className="size-3.5" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {needsPr && <p className="mt-2 text-xs text-muted-foreground">Non-preemptive priority scheduling.</p>}

            <Button variant="ghost" size="sm" className="mt-2" onClick={() => { setResult(null); setRows((r) => [...r, { at: "", bt: "", pr: "" }]); }} disabled={rows.length >= 12}>
              <Plus /> Add Process
            </Button>

            {errors.length > 0 && (
              <ul className="mt-4 space-y-1 rounded-md border border-destructive/40 p-3 text-xs text-destructive" role="alert">
                {errors.map((e) => <li key={e}>{e}</li>)}
              </ul>
            )}

            <div className="mt-5 flex gap-2">
              <Button onClick={solve} disabled={loading} className="flex-1">{loading && <Loader2 className="animate-spin" />} Solve</Button>
              <Button variant="outline" onClick={reset}><RotateCcw /> Reset</Button>
            </div>
          </fieldset>

          <section className="min-w-0 min-h-[320px] py-5 lg:pl-2" aria-live="polite" aria-label="Solution">
            {loading ? (
              <div className="flex h-full min-h-[280px] items-center justify-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" /> Solving problem...</div>
            ) : result ? (
              <ResponseView r={result} onRetry={solve} />
            ) : (
              <div className="flex h-full min-h-[280px] flex-col items-center justify-center text-center">
                <div className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Awaiting input</div>
                <p className="mt-2 max-w-sm text-sm text-muted-foreground">Your solution will appear here.</p>
              </div>
            )}
          </section>
        </div>
      </Container>
      <Footer />
    </>
  );
}
