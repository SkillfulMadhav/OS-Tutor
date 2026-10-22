import type { ReactNode } from "react";

export function PageHeader({ eyebrow, title, subtitle, children }: { eyebrow?: string; title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="mb-10 fade-up">
      {eyebrow && <div className="mb-3 font-mono text-xs uppercase tracking-widest text-primary">{eyebrow}</div>}
      <h1 className="text-3xl font-semibold sm:text-4xl">{title}</h1>
      {subtitle && <p className="mt-3 max-w-2xl text-muted-foreground">{subtitle}</p>}
      {children}
    </div>
  );
}

export function Container({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <main className={`mx-auto max-w-6xl px-4 py-10 sm:py-14 ${className}`}>{children}</main>;
}

export function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-6 text-xs text-muted-foreground sm:flex-row sm:justify-between">
        <span>OS Tutor · Operating System Theory</span>
        <span>VIT University, Vellore · CSE · 2026–27</span>
      </div>
    </footer>
  );
}
