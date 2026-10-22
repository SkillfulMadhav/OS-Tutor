import { useSyncExternalStore } from "react";
import { parseAskResponse, type AskResponse } from "@/types/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string; // user text, or empty for assistant
  response?: AskResponse;
  createdAt: number;
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: number;
  messages: ChatMessage[];
}

interface State {
  conversations: Conversation[];
  pending: Record<string, boolean>;
  loaded: boolean;
}

const KEY = "os-tutor:conversations:v1";
const EMPTY: State = { conversations: [], pending: {}, loaded: false };
let state: State = EMPTY;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

function ensureLoaded() {
  if (state.loaded || typeof window === "undefined") return;
  let conversations: Conversation[] = [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed)) conversations = parsed.filter((c) =>
      c && typeof c.id === "string" && typeof c.title === "string" && Number.isFinite(c.updatedAt) && Array.isArray(c.messages),
    ).map((c) => ({ ...c, messages: c.messages.filter((m: ChatMessage) =>
      m && typeof m.id === "string" && (m.role === "user" || m.role === "assistant") && typeof m.content === "string" && Number.isFinite(m.createdAt),
    ).map((m: ChatMessage) => ({ ...m, response: m.response ? parseAskResponse(m.response) : undefined })) }));
  } catch {
    conversations = [];
  }
  state = { conversations, pending: {}, loaded: true };
}

function persist() {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(state.conversations));
  } catch {
    /* storage full or unavailable */
  }
}

function set(next: Partial<State>) {
  state = { ...state, ...next };
  persist();
  emit();
}

export function newId() {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
}

const STOP = new Set(["what", "is", "a", "an", "the", "explain", "define", "describe", "tell", "me", "about", "teach", "of", "and", "difference", "between", "how", "does", "do", "please", "can", "you", "its", "types", "calculate", "solve", "this", "problem"]);

export function titleFrom(question: string): string {
  const clean = question.replace(/[?.!]+$/g, "").trim();
  const words = clean.split(/\s+/);
  const kept = words.filter((w) => !STOP.has(w.toLowerCase()));
  const base = (kept.length ? kept : words).slice(0, 5).join(" ").replace(/[,;:]+$/, "");
  const t = base.length > 40 ? base.slice(0, 40) + "…" : base;
  return t.charAt(0).toUpperCase() + t.slice(1) || "New conversation";
}

export const conversationStore = {
  subscribe(l: () => void) {
    listeners.add(l);
    ensureLoaded();
    if (state.loaded) queueMicrotask(l);
    return () => listeners.delete(l);
  },
  get: () => state,
  getServer: () => EMPTY,
  create(firstQuestion: string): string {
    ensureLoaded();
    const id = newId();
    const conv: Conversation = { id, title: titleFrom(firstQuestion), updatedAt: Date.now(), messages: [] };
    set({ conversations: [conv, ...state.conversations] });
    return id;
  },
  append(id: string, msg: ChatMessage) {
    ensureLoaded();
    set({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, messages: [...c.messages, msg], updatedAt: Date.now() } : c,
      ).sort((a, b) => b.updatedAt - a.updatedAt),
    });
  },
  replaceLast(id: string, msg: ChatMessage) {
    set({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, messages: [...c.messages.slice(0, -1), msg], updatedAt: Date.now() } : c,
      ),
    });
  },
  dropLast(id: string) {
    set({
      conversations: state.conversations.map((c) => (c.id === id ? { ...c, messages: c.messages.slice(0, -1) } : c)),
    });
  },
  setPending(id: string, v: boolean) {
    const pending = { ...state.pending };
    if (v) pending[id] = true;
    else delete pending[id];
    state = { ...state, pending };
    emit();
  },
  remove(id: string) {
    set({ conversations: state.conversations.filter((c) => c.id !== id) });
  },
  clear() {
    set({ conversations: [] });
  },
};

export function useConversations() {
  return useSyncExternalStore(conversationStore.subscribe, conversationStore.get, conversationStore.getServer);
}

export function relativeTime(ts: number): string {
  const s = Math.round((Date.now() - ts) / 1000);
  if (s < 60) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(ts).toLocaleDateString();
}
