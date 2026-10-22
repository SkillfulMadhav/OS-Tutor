import type { ReactNode } from "react";
import type { ProcessInput, ProcessResult } from "@/types/api";

function DataTable({ head, rows, label }: { head: string[]; rows: ReactNode[][]; label: string }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[420px] text-sm" aria-label={label}>
        <thead className="bg-surface-2 text-left text-xs uppercase tracking-wider text-muted-foreground">
          <tr>{head.map((h) => <th key={h} scope="col" className="px-3 py-2 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody className="font-mono">
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-border">
              {r.map((c, j) => <td key={j} className={`px-3 py-2 ${j === 0 ? "font-semibold" : ""}`}>{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ProcessTable({ processes }: { processes: ProcessInput[] }) {
  const hasPriority = processes.some((p) => p.priority !== undefined && p.priority !== null);
  const head = ["Process", "Arrival Time", "Burst Time", ...(hasPriority ? ["Priority"] : [])];
  return (
    <DataTable
      label="Input processes"
      head={head}
      rows={processes.map((p) => [p.id, p.arrival_time, p.burst_time, ...(hasPriority ? [p.priority ?? "—"] : [])])}
    />
  );
}

export function ResultTable({ results }: { results: ProcessResult[] }) {
  return (
    <DataTable
      label="Process calculations"
      head={["Process", "Completion Time", "Turnaround Time", "Waiting Time"]}
      rows={results.map((r) => [r.id, r.completion_time, r.turnaround_time, r.waiting_time])}
    />
  );
}

export function SolutionSummary({ awt, atat }: { awt: number; atat: number }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {([{ label: "Average Waiting Time", value: awt }, { label: "Average Turnaround Time", value: atat }]).map(({ label, value }) => (
        <div key={label} className="min-w-0 rounded-lg border border-border bg-surface-2 p-4">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
          <div title={`Exact value: ${value}`} className="mt-1 break-all font-mono text-3xl font-semibold text-primary">{value.toLocaleString("en-US", { maximumFractionDigits: 2 })}</div>
        </div>
      ))}
    </div>
  );
}
