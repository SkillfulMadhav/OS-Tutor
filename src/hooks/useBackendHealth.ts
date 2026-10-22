import { useCallback, useEffect, useSyncExternalStore } from "react";
import { health } from "@/services/api";

export type BackendStatus = "checking" | "connected" | "starting" | "unavailable";
let status: BackendStatus = "checking";
let inflight: Promise<void> | null = null;
let started = false;
let timer: ReturnType<typeof setTimeout> | null = null;
const listeners = new Set<() => void>();

function schedule() {
  if (timer) clearTimeout(timer);
  // Check often while the backend is starting, otherwise once a minute.
  timer = setTimeout(() => void check(), status === "starting" || status === "unavailable" ? 10_000 : 60_000);
}

function check() {
  if (inflight) return inflight;
  if (status !== "connected" && status !== "starting") {
    status = "checking";
    listeners.forEach((l) => l());
  }
  inflight = health().then((h) => {
    status = h === "ok" ? "connected" : h === "loading" ? "starting" : "unavailable";
    inflight = null;
    listeners.forEach((l) => l());
    schedule();
  });
  return inflight;
}

export function useBackendHealth() {
  const s = useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => status,
    () => "checking" as BackendStatus,
  );
  useEffect(() => {
    if (!started) {
      started = true;
      void check();
    }
    const onVisible = () => { if (document.visibilityState === "visible") void check(); };
    window.addEventListener("online", check);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("online", check);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);
  const recheck = useCallback(() => check(), []);
  return { status: s, recheck };
}
