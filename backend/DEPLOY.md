# Deploy OS Tutor backend free (Render + Groq)

Theory: same BGE + FAISS retrieval, prompts and cleanup; answers written by a Groq-hosted Qwen (`GROQ_MODEL`). Numericals: unchanged solver.

1. Put `chunks.pkl`, `embeddings.npy`, `faiss.index` in `backend/data/` (Git LFS for files over 100 MB).
2. Push the repo to GitHub (Lovable → GitHub → Connect).
3. render.com → New → Blueprint → pick the repo (uses `render.yaml`, Free plan).
4. Paste your Groq key into `GROQ_API_KEY` when asked.
5. Wait for `https://<service>.onrender.com/api/health` to return `{"status":"ok"}`.
6. Add the published website address to `CORS_ORIGINS` (comma-separated).

Free plan: sleeps after ~15 min idle, wakes in up to a minute, 512 MB memory.
Groq limits are per account and can change; see console.groq.com/settings/limits.
Local GPU mode is still available: `GENERATOR=local` with `requirements.txt`.
