import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { ArrowRight, BookOpen, Calculator, MessageSquare, Sigma } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Container, Footer } from "@/components/Layout/Page";
import { relativeTime, useConversations } from "@/hooks/useConversations";
import { useState } from "react";
import processor from "@/assets/processor.jpg";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "OS Tutor — Learn Operating Systems" },
      { name: "description", content: "Ask questions, explore topics and solve CPU scheduling problems with exact Gantt charts. Built for VIT's Operating System Theory course." },
      { property: "og:title", content: "OS Tutor — Learn Operating Systems" },
      { property: "og:description", content: "Course-grounded OS explanations and exact numerical problem solving." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Home,
});

const FEATURES = [
  { icon: MessageSquare, title: "Ask Tutor", text: "Ask questions about Operating Systems and receive course-grounded explanations.", cta: "Ask a question", to: "/ask" },
  { icon: Calculator, title: "Numerical Lab", text: "Solve CPU scheduling problems with exact calculations and visual Gantt charts.", cta: "Solve a problem", to: "/numerical" },
  { icon: BookOpen, title: "Explore Topics", text: "Study Operating Systems concepts organized into focused topics.", cta: "Explore topics", to: "/topics" },
  { icon: Sigma, title: "Formula Reference", text: "Quickly review important formulas used in OS problems.", cta: "View formulas", to: "/formulas" },
] as const;

const THEORY = [
  "What is a process?",
  "Explain semaphore.",
  "What is the difference between paging and segmentation?",
  "Explain deadlock.",
  "What is TLB?",
  "Explain FCFS scheduling.",
];
const NUMERICAL = [
  "Calculate FCFS waiting time for P1(0,5), P2(1,3), P3(2,8)",
  "Solve this SJF problem: P1(0,7), P2(0,3), P3(0,5)",
  "Calculate Round Robin with quantum 3 for P1(0,5), P2(1,3), P3(2,2)",
];

function Example({ q, mono }: { q: string; mono?: boolean }) {
  return (
    <Link to="/ask" search={{ q }} className="group flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3 text-sm transition-colors hover:border-primary/50">
      <span className={mono ? "font-mono text-[13px]" : ""}>{q}</span>
      <ArrowRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" aria-hidden />
    </Link>
  );
}

function Home() {
  const { conversations } = useConversations();
  const [question, setQuestion] = useState("");
  const navigate = useNavigate();
  return (
    <>
      <section className="study-hero relative overflow-hidden border-b border-border">
        <img src={processor} width={1600} height={912} fetchPriority="high" alt="" className="absolute inset-0 h-full w-full object-cover object-right" />
        <div className="relative z-10 mx-auto max-w-6xl px-4 py-14 sm:py-20">
          <div className="hero-muted mb-5 flex items-center gap-2 font-mono text-[11px] sm:text-xs fade-up">
            <span className="size-1.5 rounded-full bg-primary" aria-hidden /> Operating System Theory · VIT University • CSE
          </div>
          <h1 className="max-w-3xl text-5xl leading-tight font-semibold sm:text-7xl fade-up">
            OS Tutor<span className="text-primary">.</span>
          </h1>
          <p className="mt-4 max-w-xl text-2xl font-display fade-up">Understand the theory.<br />Work through the numbers.</p>
          <p className="hero-muted mt-4 max-w-lg text-base fade-up">
            Operating Systems, grounded in your course notes. From processes and paging to CPU scheduling.
          </p>
          <form className="mt-7 flex max-w-xl items-center gap-2 rounded-lg border border-input bg-background p-2" onSubmit={(e) => { e.preventDefault(); if (question.trim()) void navigate({ to: "/ask", search: { q: question.trim() } }); }}>
            <label htmlFor="home-question" className="sr-only">Ask an Operating Systems question</label>
            <input id="home-question" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="What would you like to understand?" className="h-10 min-w-0 flex-1 bg-transparent px-2 text-sm text-foreground outline-none" />
            <Button type="submit" size="icon" disabled={!question.trim()} aria-label="Open question in tutor"><ArrowRight /></Button>
          </form>
          <div className="mt-4 flex flex-wrap gap-3 fade-up">
            <Button asChild variant="secondary"><Link to="/ask"><MessageSquare /> Ask Tutor</Link></Button>
            <Button asChild variant="secondary"><Link to="/numerical"><Calculator /> Numerical Lab</Link></Button>
          </div>
        </div>
      </section>

      <Container>
        <section aria-labelledby="features" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <h2 id="features" className="sr-only">Features</h2>
          {FEATURES.map((f) => (
            <Link key={f.title} to={f.to} className="card-surface group flex flex-col p-6 transition-colors hover:border-primary/50">
              <f.icon className="size-5 text-primary" aria-hidden />
              <h3 className="mt-5 text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 flex-1 text-sm text-muted-foreground">{f.text}</p>
              <span className="mt-5 inline-flex items-center gap-1 text-sm font-medium">{f.cta} <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden /></span>
            </Link>
          ))}
        </section>

        <section className="mt-20" aria-labelledby="ask">
          <h2 id="ask" className="text-2xl font-semibold">What can I ask?</h2>
          <p className="mt-2 text-muted-foreground">Just type naturally — OS Tutor works out whether it's a concept or a calculation.</p>
          <div className="mt-8 grid gap-8 lg:grid-cols-2">
            <div>
              <h3 className="mb-3 font-mono text-xs uppercase tracking-widest text-muted-foreground">Theory</h3>
              <div className="grid gap-2">{THEORY.map((q) => <Example key={q} q={q} />)}</div>
            </div>
            <div>
              <h3 className="mb-3 font-mono text-xs uppercase tracking-widest text-muted-foreground">Numerical</h3>
              <div className="grid gap-2">{NUMERICAL.map((q) => <Example key={q} q={q} mono />)}</div>
            </div>
          </div>
        </section>

        <section className="mt-20" aria-labelledby="recent">
          <h2 id="recent" className="text-2xl font-semibold">Recent activity</h2>
          {conversations.length === 0 ? (
            <div className="mt-6 flex flex-col items-start gap-4 border-t border-border py-6 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-muted-foreground">Your recent questions will appear here.</p>
              <Button asChild variant="secondary"><Link to="/ask">Start learning</Link></Button>
            </div>
          ) : (
            <ul className="mt-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {conversations.slice(0, 6).map((c) => (
                <li key={c.id}>
                  <Link to="/ask/$threadId" params={{ threadId: c.id }} className="card-surface block p-4 transition-colors hover:border-primary/50">
                    <div className="truncate font-medium">{c.title}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{relativeTime(c.updatedAt)} · {c.messages.filter((m) => m.role === "user").length} questions</div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </Container>
      <Footer />
    </>
  );
}
