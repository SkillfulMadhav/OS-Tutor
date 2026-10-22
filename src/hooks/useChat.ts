import { useCallback } from "react";
import { ask } from "@/services/api";
import { conversationStore, newId, useConversations } from "./useConversations";

/** Sends a question to the backend and records both sides in local history. */
export function useChat(threadId: string | undefined) {
  const { conversations, pending, loaded } = useConversations();
  const conversation = threadId ? conversations.find((c) => c.id === threadId) : undefined;
  const isPending = threadId ? !!pending[threadId] : false;

  const run = useCallback(async (id: string, question: string) => {
    conversationStore.setPending(id, true);
    const response = await ask(question);
    conversationStore.append(id, { id: newId(), role: "assistant", content: "", response, createdAt: Date.now() });
    conversationStore.setPending(id, false);
  }, []);

  /** Returns the thread id used (creates one if needed). */
  const send = useCallback(
    (question: string): string | null => {
      const q = question.trim();
      if (!q) return null;
      let id = threadId;
      if (id && conversationStore.get().pending[id]) return null;
      if (!id || !conversationStore.get().conversations.some((c) => c.id === id)) id = conversationStore.create(q);
      conversationStore.append(id, { id: newId(), role: "user", content: q, createdAt: Date.now() });
      void run(id, q);
      return id;
    },
    [threadId, run],
  );

  /** Retry the last question (removes the failed assistant reply). */
  const retry = useCallback(() => {
    if (!threadId) return;
    const conv = conversationStore.get().conversations.find((c) => c.id === threadId);
    if (!conv) return;
    const lastUser = [...conv.messages].reverse().find((m) => m.role === "user");
    const last = conv.messages[conv.messages.length - 1];
    if (!lastUser || conversationStore.get().pending[threadId]) return;
    if (last?.role === "assistant") conversationStore.dropLast(threadId);
    void run(threadId, lastUser.content);
  }, [threadId, run]);

  return { conversation, isPending, loaded, send, retry };
}
