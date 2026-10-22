import { createFileRoute } from "@tanstack/react-router";
import { Search } from "lucide-react";
import { useState } from "react";
import { Container, Footer, PageHeader } from "@/components/Layout/Page";

export const Route = createFileRoute("/formulas")({
  head: () => ({
    meta: [
      { title: "Formula Reference — OS Tutor" },
      { name: "description", content: "Searchable reference of CPU scheduling formulas: turnaround time, waiting time, averages and response time." },
      { property: "og:title", content: "Formula Reference — OS Tutor" },
      { property: "og:description", content: "Key Operating Systems formulas at a glance." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Formulas,
});

interface Formula { name: string; expr: string; terms: string; section: string }

/** Extend this list as course material provides more formulas. */
const FORMULAS: Formula[] = [
  { section: "CPU Scheduling", name: "Turnaround Time", expr: "TAT = Completion Time − Arrival Time", terms: "TAT, CT, AT" },
  { section: "CPU Scheduling", name: "Waiting Time", expr: "WT = Turnaround Time − Burst Time", terms: "WT, TAT, BT" },
  { section: "CPU Scheduling", name: "Average Waiting Time", expr: "Avg WT = (Σ WTᵢ) / n", terms: "n = number of processes" },
  { section: "CPU Scheduling", name: "Average Turnaround Time", expr: "Avg TAT = (Σ TATᵢ) / n", terms: "n = number of processes" },
  { section: "CPU Scheduling", name: "Response Time", expr: "RT = First CPU Start Time − Arrival Time", terms: "RT, AT" },
];

function Formulas() {
  const [q, setQ] = useState("");
  const list = FORMULAS.filter((f) => (f.name + f.expr + f.terms).toLowerCase().includes(q.toLowerCase()));
  const sections = Array.from(new Set(list.map((f) => f.section)));
  return (
    <>
      <Container>
        <PageHeader eyebrow="Reference" title="Formulas" subtitle="The core formulas used in Operating Systems numericals." />
        <label className="relative mb-10 block max-w-md">
          <span className="sr-only">Search formulas</span>
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search formulas" className="h-10 w-full rounded-lg border border-input bg-card pr-3 pl-9 text-sm placeholder:text-muted-foreground" />
        </label>
        {sections.length === 0 && <p className="text-muted-foreground">No formulas match "{q}".</p>}
        {sections.map((s) => (
          <section key={s} className="mb-12">
            <h2 className="mb-4 font-mono text-xs uppercase tracking-widest text-muted-foreground">{s}</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {list.filter((f) => f.section === s).map((f) => (
                <article key={f.name} className="card-surface p-5">
                  <h3 className="text-sm font-medium text-muted-foreground">{f.name}</h3>
                  <p className="mt-3 break-words font-mono text-base leading-relaxed text-primary">{f.expr}</p>
                  <p className="mt-3 font-mono text-xs text-muted-foreground">{f.terms}</p>
                </article>
              ))}
            </div>
          </section>
        ))}
      </Container>
      <Footer />
    </>
  );
}
