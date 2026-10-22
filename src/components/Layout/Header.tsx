import { Link, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { Menu, Moon, Sun, Cpu, LogOut } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useAuthUser } from "@/hooks/useAuth";
import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { USE_MOCK_API } from "@/services/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export const NAV = [
  { to: "/", label: "Home" },
  { to: "/ask", label: "Ask Tutor" },
  { to: "/numerical", label: "Numerical Lab" },
  { to: "/topics", label: "Topics" },
  { to: "/formulas", label: "Formulas" },
  { to: "/evaluate", label: "Evaluation" },
  { to: "/progress", label: "Understanding" },
] as const;

function Account() {
  const user = useAuthUser();
  const navigate = useNavigate();
  const qc = useQueryClient();
  if (user === undefined) return null;
  if (!user) return <Button asChild size="sm" variant="outline"><Link to="/auth" search={{ redirect: undefined }}>Sign in</Link></Button>;
  async function out() {
    await qc.cancelQueries();
    qc.clear();
    await supabase.auth.signOut();
    void navigate({ to: "/auth", search: { redirect: undefined }, replace: true });
  }
  return (
    <Button size="sm" variant="ghost" onClick={() => void out()} title={user.email ?? "Signed in"} aria-label="Sign out" className="text-muted-foreground">
      <LogOut className="size-4" /><span className="hidden xl:inline">Sign out</span>
    </Button>
  );
}

export function Logo() {
  return (
    <Link to="/" className="flex shrink-0 items-center gap-2 font-display text-[15px] font-semibold" aria-label="OS Tutor home">
      <span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground">
        <Cpu className="size-4" aria-hidden />
      </span>
      OS Tutor
    </Link>
  );
}

export function BackendStatus({ compact = false }: { compact?: boolean }) {
  const { status, recheck } = useBackendHealth();
  const label =
    status === "connected" ? "Tutor online" :
    status === "unavailable" ? "Connection issue" :
    status === "starting" ? "Tutor warming up" : "Connecting to tutor";
  return (
    <Button variant="ghost" size="sm" onClick={() => void recheck()} title={status === "unavailable" ? "Unable to reach the tutor. Click to retry." : label} className="inline-flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground" aria-label={`${label}. Check connection`}>
      <span
        aria-hidden
        className={cn(
          "size-2 rounded-full",
          status === "connected" && "bg-success",
          status === "unavailable" && "bg-destructive",
          status === "starting" && "animate-pulse bg-primary",
          status === "checking" && "animate-pulse bg-muted-foreground",
        )}
      />
      <span className={cn(compact && "sr-only sm:not-sr-only")}>{label}</span>
    </Button>
  );
}

export function MockBadge() {
  if (!USE_MOCK_API) return null;
  return (
    <span className="rounded-md border border-primary/40 bg-accent px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-accent-foreground">
      Demo / Mock Mode
    </span>
  );
}

function ThemeToggle() {
  const [dark, setDark] = useState(true);
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("os-tutor:theme", next ? "dark" : "light");
    } catch {
      /* ignore */
    }
  };
  return (
    <Button variant="ghost" size="icon"
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      className="grid size-8 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
    >
      {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}

const linkCls = "rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground";
const activeCls = "bg-secondary text-foreground";

export function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 h-14 border-b border-border bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-full max-w-[1400px] items-center gap-4 px-4">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
             <Button variant="ghost" size="icon" className="size-8 lg:hidden" aria-label="Open menu">
              <Menu className="size-5" />
             </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 bg-sidebar">
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <div className="mt-2 mb-6"><Logo /></div>
            <nav className="flex flex-col gap-1" aria-label="Main">
              {NAV.map((n) => (
                <Link key={n.to} to={n.to} onClick={() => setOpen(false)} className={linkCls} activeProps={{ className: activeCls }} activeOptions={{ exact: n.to === "/" }}>
                  {n.label}
                </Link>
              ))}
            </nav>
            <div className="mt-6 flex flex-col gap-2"><BackendStatus /><MockBadge /></div>
          </SheetContent>
        </Sheet>
        <Logo />
        <nav className="ml-4 hidden items-center gap-1 lg:flex" aria-label="Main">
          {NAV.map((n) => (
            <Link key={n.to} to={n.to} className={linkCls} activeProps={{ className: activeCls }} activeOptions={{ exact: n.to === "/" }}>
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <span className="hidden md:inline"><MockBadge /></span>
          <BackendStatus compact />
          <ThemeToggle />
          <Account />
        </div>
      </div>
    </header>
  );
}
