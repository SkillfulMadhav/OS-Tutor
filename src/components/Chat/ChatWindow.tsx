import { useNavigate } from "@tanstack/react-router";
import { ArrowUp, Cpu, PanelLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { ChatSidebar } from "./ChatSidebar";
import { ResponseView } from "@/components/Responses/Responses";
import { useChat } from "@/hooks/useChat";
import type { ChatMessage as Msg } from "@/hooks/useConversations";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const CHIPS = [
  { label: "Theory", text: "Explain " },
  { label: "Numerical", text: "Calculate FCFS for P1(0,5), P2(1,3), P3(2,8)" },
  { label: "Explain simply", text: "Explain simply: " },
  { label: "Formula", text: "What is the formula for " },
];

const EXAMPLES = [
  { title: "Explain Deadlock", q: "Explain deadlock." },
  { title: "Explain Paging", q: "Explain paging." },
  { title: "Solve FCFS", q: "Calculate FCFS waiting time for P1(0,5), P2(1,3), P3(2,8)" },
  { title: "Explain Semaphores", q: "Explain semaphore and its types." },
];

const time = (t: number) => new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 fade-up" role="status" aria-live="polite">
      <TutorMark />
      <span className="flex items-center gap-1" aria-hidden>
        {[0, 1, 2].map((i) => <span key={i} className="size-1.5 animate-bounce rounded-full bg-primary" style={{ animationDelay: `${i * 120}ms` }} />)}
      </span>
      <span className="text-sm text-muted-foreground">OS Tutor is thinking...</span>
    </div>
  );
}

function TutorMark() {
  return <span className="grid size-7 shrink-0 place-items-center rounded-md border border-border bg-surface-2 text-primary"><Cpu className="size-3.5" aria-hidden /></span>;
}

function ChatMessage({ m, onFollowUp, onRetry }: { m: Msg; onFollowUp: (t: string) => void; onRetry: () => void }) {
  if (m.role === "user") {
    return (
      <div className="flex flex-col items-end fade-up">
        <div className="max-w-[85%] break-words rounded-lg rounded-br-sm bg-secondary px-4 py-2.5 whitespace-pre-wrap text-secondary-foreground">{m.content}</div>
        <time className="mt-1 text-[11px] text-muted-foreground">{time(m.createdAt)}</time>
      </div>
    );
  }
  return (
    <div className="flex gap-3 fade-up">
      <TutorMark />
      <div className="min-w-0 flex-1">
        <div className="mb-2 flex items-baseline gap-2 text-sm"><span className="font-display font-semibold">OS Tutor</span><time className="text-[11px] text-muted-foreground">{time(m.createdAt)}</time></div>
        {m.response ? <ResponseView r={m.response} onFollowUp={onFollowUp} onRetry={onRetry} /> : null}
      </div>
    </div>
  );
}

export function ChatWindow({ threadId, initialQuestion }: { threadId?: string | undefined; initialQuestion?: string | undefined }) {
  const navigate = useNavigate();
  const { conversation, isPending, loaded, send, retry } = useChat(threadId);
  const [input, setInput] = useState(initialQuestion ?? "");
  const [drawer, setDrawer] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const messages = conversation?.messages ?? [];

  useEffect(() => { if (initialQuestion) setInput(initialQuestion); }, [initialQuestion]);
  useEffect(() => { inputRef.current?.focus(); }, [threadId, isPending]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "end" }); }, [messages.length, isPending]);
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [input]);

  // Unknown thread id after load → back to new chat
  useEffect(() => {
    if (threadId && loaded && !conversation) void navigate({ to: "/ask", replace: true });
  }, [threadId, loaded, conversation, navigate]);

  const submit = (text = input) => {
    if (isPending || !text.trim()) return;
    const id = send(text);
    if (!id) return;
    setInput("");
    if (id !== threadId) void navigate({ to: "/ask/$threadId", params: { threadId: id } });
  };

  const insert = (t: string) => {
    setInput(t);
    requestAnimationFrame(() => {
      const el = inputRef.current;
      el?.focus();
      el?.setSelectionRange(t.length, t.length);
    });
  };

  return (
    <div className="flex h-[calc(100dvh-3.5rem)]">
      <aside className="hidden w-72 shrink-0 border-r border-sidebar-border bg-sidebar md:block" aria-label="Conversations">
        <ChatSidebar activeId={threadId} />
      </aside>
      <Sheet open={drawer} onOpenChange={setDrawer}>
        <SheetContent side="left" className="w-80 bg-sidebar p-0">
          <SheetTitle className="sr-only">Conversations</SheetTitle>
          <ChatSidebar activeId={threadId} onNavigate={() => setDrawer(false)} />
        </SheetContent>
      </Sheet>

      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-3 border-b border-border px-4 py-3">
          <Button variant="ghost" size="icon" className="size-8 md:hidden" aria-label="Open conversations" onClick={() => setDrawer(true)}>
            <PanelLeft className="size-4" />
          </Button>
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold">{conversation?.title ?? "Ask Tutor"}</h1>
            <p className="truncate text-xs text-muted-foreground">Ask a theory question or solve an Operating Systems numerical.</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-4 py-6">
            {messages.length === 0 && !isPending ? (
              <div className="flex min-h-[50vh] flex-col items-center justify-center text-center fade-up">
                <span className="mb-5 grid size-12 place-items-center rounded-xl border border-border bg-surface-2 text-primary"><Cpu className="size-6" aria-hidden /></span>
                <h2 className="text-2xl font-semibold">How can I help you learn Operating Systems?</h2>
                <p className="mt-2 text-muted-foreground">Ask about a concept, formula, or numerical problem.</p>
                <div className="mt-8 grid w-full max-w-xl gap-2 sm:grid-cols-2">
                  {EXAMPLES.map((e) => (
                    <Button variant="outline" key={e.title} onClick={() => insert(e.q)} className="h-auto min-w-0 flex-col items-start gap-0 whitespace-normal p-4 text-left">
                      <div className="font-medium">{e.title}</div>
                      <div className="mt-1 line-clamp-2 font-mono text-xs text-muted-foreground">{e.q}</div>
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-8">
                {messages.map((m) => <ChatMessage key={m.id} m={m} onFollowUp={insert} onRetry={retry} />)}
                {isPending && <TypingIndicator />}
              </div>
            )}
            <div ref={endRef} />
          </div>
        </div>

        <div className="border-t border-border bg-background px-4 pt-3 pb-4">
          <div className="mx-auto max-w-3xl">
            <div className="mb-2 flex flex-wrap gap-1.5" aria-label="Quick prompts">
              {CHIPS.map((c) => (
                <Button variant="outline" size="sm" key={c.label} onClick={() => insert(c.text)} className="h-7 text-xs text-muted-foreground">
                  {c.label}
                </Button>
              ))}
            </div>
            <form
              onSubmit={(e) => { e.preventDefault(); submit(); }}
              className="flex items-end gap-2 rounded-lg border border-input bg-card p-2 focus-within:border-primary/60"
            >
              <label htmlFor="chat-input" className="sr-only">Your question</label>
              <textarea
                id="chat-input"
                ref={inputRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); } }}
                placeholder="Ask an Operating Systems question..."
                className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-2 text-[15px] outline-none placeholder:text-muted-foreground focus-visible:outline-none"
              />
              <Button size="icon"
                type="submit"
                disabled={isPending || !input.trim()}
                aria-label="Send"
                className={cn("size-9 shrink-0")}
              >
                <ArrowUp className="size-4" />
              </Button>
            </form>
            <p className="mt-2 text-center text-[11px] text-muted-foreground">Check important answers against your course notes.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
