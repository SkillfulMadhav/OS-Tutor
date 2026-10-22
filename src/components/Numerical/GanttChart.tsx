import type { GanttBlock } from "@/types/api";

const PALETTE = ["bg-chart-1/25 border-chart-1/60", "bg-chart-2/25 border-chart-2/60", "bg-chart-3/25 border-chart-3/60", "bg-chart-4/25 border-chart-4/60", "bg-chart-5/25 border-chart-5/60"];

export function GanttChart({ blocks }: { blocks: GanttBlock[] }) {
  const first = blocks[0];
  const last = blocks.at(-1);
  if (!first || !last) return <p className="text-sm text-muted-foreground">No Gantt chart data returned.</p>;
  const start = first.start;
  const end = last.end;
  const total = Math.max(end - start, 1);
  const ids = Array.from(new Set(blocks.map((b) => b.process).filter((p) => p.toUpperCase() !== "IDLE")));
  const ticks = [start, ...blocks.map((b) => b.end)];
  const shortest = Math.min(...blocks.map((b) => b.end - b.start).filter((n) => n > 0));
  const minWidth = Math.max(blocks.length * 64, 480, total / (Number.isFinite(shortest) ? shortest : 1) * 48);

  return (
    <div className="overflow-x-auto pb-2" role="region" aria-label="CPU Gantt chart" tabIndex={0}>
      <div style={{ minWidth }} className="px-3">
        <div className="flex h-14 overflow-hidden rounded-lg border border-border">
          {blocks.map((b, i) => {
            const idle = b.process.toUpperCase() === "IDLE";
            const w = ((b.end - b.start) / total) * 100;
            return (
              <div
                key={i}
                style={{ width: `${w}%` }}
                className={`flex flex-col items-center justify-center border-r last:border-r-0 font-mono text-xs ${
                  idle ? "bg-[repeating-linear-gradient(135deg,var(--color-surface-2)_0_6px,transparent_6px_12px)] border-border text-muted-foreground" : PALETTE[ids.indexOf(b.process) % PALETTE.length]
                }`}
                title={`${b.process}: ${b.start}–${b.end}`}
              >
                <span className="font-semibold">{b.process}</span>
                <span className="text-[10px] text-muted-foreground">{b.start}–{b.end}</span>
              </div>
            );
          })}
        </div>
        <div className="relative mt-1 h-5 font-mono text-[11px] text-muted-foreground">
          {ticks.map((t, i) => (
            <span key={i} className="absolute -translate-x-1/2" style={{ left: `${((t - start) / total) * 100}%` }}>
              {t}
            </span>
          ))}
        </div>
      </div>
      <ul className="sr-only">
        {blocks.map((b, i) => <li key={i}>{b.process} runs from {b.start} to {b.end}</li>)}
      </ul>
    </div>
  );
}
