import { createFileRoute } from "@tanstack/react-router";
import { ChatWindow } from "@/components/Chat/ChatWindow";

export const Route = createFileRoute("/ask/$threadId")({
  head: () => ({
    meta: [
      { title: "Conversation — OS Tutor" },
      { name: "description", content: "Your OS Tutor conversation." },
      { property: "og:title", content: "Conversation — OS Tutor" },
      { property: "og:description", content: "Your OS Tutor conversation." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Thread,
});

function Thread() {
  const { threadId } = Route.useParams();
  return <ChatWindow key={threadId} threadId={threadId} />;
}
