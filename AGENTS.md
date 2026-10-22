<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Architecture
- All backend calls go through `src/services/api.ts`; the FastAPI backend (VITE_API_BASE_URL) is the only source of answers and numerical results — never compute scheduling results in the frontend.
- Mock data lives only in `src/services/mockApi.ts`, loaded when VITE_USE_MOCK_API=true, so production components never contain fake responses.
- Backend payloads are validated in `src/types/api.ts` before rendering so malformed data can't crash the UI.
- Chat history is a localStorage store (`useConversations`) with one URL per thread (`/ask/$threadId`), kept swappable for a database later.
- Backend has two answer-writing modes via GENERATOR: 'local' (Qwen3-8B GPU) and 'groq' (CPU hosting on Render); retrieval, prompts and cleanup are shared so both behave the same.
- Browser origins must be explicitly allowed on Render, including both the editor's lovableproject.com origin and preview/published origins; an online API alone does not establish browser connectivity.
- Evaluation questions come only from the backend `/api/quiz`, generated from retrieved course chunks and strictly validated; never hardcode or invent questions in the frontend.
- Student accounts and understanding scores live in Lovable Cloud (`topic_progress`); scoring is applied atomically by the `record_answer` database function so the UI never computes stored scores.
- Validate persisted conversations and source citation fields before rendering; browser storage and backend metadata are untrusted input.
