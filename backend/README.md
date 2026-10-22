# OS Tutor backend (FastAPI)

Wraps the Kaggle OSTutor code: `rag.py` (theory RAG + Qwen3-8B, cleanup pipeline unchanged) and `numerical.py` (solvers + router, unchanged). `main.py` only translates results into the frontend's JSON.

Needs an NVIDIA GPU (~6–8 GB VRAM, CUDA) for Qwen3-8B 4-bit. Without one, start with `SKIP_MODEL_LOAD=1`: numericals work, theory returns an error.

## Setup
Copy `chunks.pkl`, `embeddings.npy`, `faiss.index` into `backend/data/` (or set `RAG_DATA_DIR`).

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
# numericals only, no GPU:  SKIP_MODEL_LOAD=1 uvicorn main:app --port 8000
```

Env vars: `RAG_DATA_DIR`, `MODEL_NAME`, `EMBED_MODEL`, `CORS_ORIGINS` (comma-separated), `SKIP_MODEL_LOAD`.

## Tests
```bash
curl localhost:8000/api/health
A='curl -s -X POST localhost:8000/api/ask -H Content-Type:application/json -d'
$A '{"question":"What is FCFS and how is waiting time calculated?"}'
$A '{"question":"Calculate FCFS for P1(0,5) P2(1,3) P3(2,8)"}'
$A '{"question":"Calculate Round Robin for P1(0,5) P2(1,3) quantum = 2"}'
$A '{"question":"Calculate FCFS"}'
$A '{"question":"Calculate Preemptive Priority Scheduling for P1(0,5,2) P2(1,3,1)"}'
```

## Connect the app
Set `VITE_USE_MOCK_API=false` and `VITE_API_BASE_URL=http://localhost:8000`.
