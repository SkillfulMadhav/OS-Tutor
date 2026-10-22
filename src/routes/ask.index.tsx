import { createFileRoute } from "@tanstack/react-router";
import { ChatWindow } from "@/components/Chat/ChatWindow";

export const Route = createFileRoute("/ask/")({
  validateSearch: (s: Record<string, unknown>): { q?: string | undefined } => ({ q: typeof s["q"] === "string" ? (s["q"] as string) : undefined }),
  head: () => ({
    meta: [
      { title: "Ask Tutor — OS Tutor" },
      { name: "description", content: "Ask any Operating Systems theory question or numerical problem and get a course-grounded answer." },
      { property: "og:title", content: "Ask Tutor — OS Tutor" },
      { property: "og:description", content: "Ask any Operating Systems theory question or numerical problem." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AskIndex,
});

function AskIndex() {
  const { q } = Route.useSearch();
  return <ChatWindow key="new" initialQuestion={q} />;
}
