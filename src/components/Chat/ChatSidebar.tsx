import { Link, useNavigate } from "@tanstack/react-router";
import { MessageSquare, Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { conversationStore, relativeTime, useConversations } from "@/hooks/useConversations";
import { cn } from "@/lib/utils";

export function ChatSidebar({ activeId, onNavigate }: { activeId?: string | undefined; onNavigate?: (() => void) | undefined }) {
  const { conversations } = useConversations();
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const list = conversations.filter((c) => c.title.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="flex h-full flex-col gap-3 p-3">
      <Button asChild className="w-full justify-start">
        <Link to="/ask" onClick={onNavigate}><Plus /> New Chat</Link>
      </Button>
      <label className="relative block">
        <span className="sr-only">Search conversations</span>
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search conversations"
          className="h-8 w-full rounded-md border border-input bg-background pr-2 pl-8 text-sm placeholder:text-muted-foreground"
        />
      </label>
      <div className="px-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">Recent Conversations</div>
      <ul className="-mx-1 flex-1 space-y-0.5 overflow-y-auto">
        {list.length === 0 && <li className="px-2 py-2 text-sm text-muted-foreground">{q ? "No matches." : "No conversations yet."}</li>}
        {list.map((c) => (
          <li key={c.id} className={cn("group flex items-center rounded-md", c.id === activeId ? "bg-sidebar-accent" : "hover:bg-sidebar-accent/60")}>
            <Link
              to="/ask/$threadId"
              params={{ threadId: c.id }}
              onClick={onNavigate}
              className="flex min-w-0 flex-1 items-start gap-2 px-2 py-2"
              aria-current={c.id === activeId ? "page" : undefined}
            >
              <MessageSquare className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden />
              <span className="min-w-0">
                <span className="block truncate text-sm">{c.title}</span>
                <span className="block text-[11px] text-muted-foreground">{relativeTime(c.updatedAt)}</span>
              </span>
            </Link>
            <button
              onClick={() => {
                conversationStore.remove(c.id);
                if (c.id === activeId) void navigate({ to: "/ask" });
              }}
              className="mr-1 grid size-7 shrink-0 place-items-center rounded text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:text-destructive focus-visible:opacity-100"
              aria-label={`Delete conversation ${c.title}`}
            >
              <Trash2 className="size-3.5" />
            </button>
          </li>
        ))}
      </ul>
      <nav className="grid grid-cols-2 gap-1 border-t border-sidebar-border pt-3 text-sm" aria-label="Sections">
        {(["/", "/topics", "/formulas"] as const).map((to) => (
          <Link key={to} to={to} onClick={onNavigate} className="rounded-md px-2 py-1.5 text-muted-foreground hover:bg-sidebar-accent hover:text-foreground">
            {to === "/" ? "Home" : to.slice(1, 2).toUpperCase() + to.slice(2)}
          </Link>
        ))}
      </nav>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="ghost" size="sm" className="justify-start text-muted-foreground" disabled={!conversations.length}>
            <Trash2 /> Clear history
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Clear all conversations?</AlertDialogTitle>
            <AlertDialogDescription>This removes every saved conversation from this browser. It can't be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => { conversationStore.clear(); void navigate({ to: "/ask" }); }}>Clear history</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
