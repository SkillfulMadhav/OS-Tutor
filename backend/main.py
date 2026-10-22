"""OS Tutor FastAPI backend.

Thin wrapper: calls answer_question(question, theory_fn=ask_ostutor) and
translates its result into the frontend's response types. No scheduling
or answer logic lives here.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import config
import numerical
import quiz
import rag

NOT_AVAILABLE = "That information is not available in the provided course material."


@asynccontextmanager
async def lifespan(_app):
    # Load in the background so /api/health answers "loading" immediately.
    if not config.SKIP_MODEL_LOAD:
        import threading
        threading.Thread(target=rag.load, daemon=True).start()
    yield


app = FastAPI(title="OS Tutor API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


def _err(message):
    return {"type": "error", "message": message}


@app.exception_handler(RequestValidationError)
async def _bad_request(_req: Request, _exc):
    return JSONResponse(status_code=422, content=_err('Send a JSON body like {"question": "..."}.'))


@app.get("/api/health")
def health():
    if config.SKIP_MODEL_LOAD or rag.LOADED:
        return {"status": "ok", "theory_model": rag.LOADED}
    if rag.LOAD_ERROR:
        return {"status": "degraded", "error": rag.LOAD_ERROR}
    return {"status": "loading"}


def theory_fn(question):
    if not rag.LOADED:
        raise RuntimeError("theory model not loaded")
    return rag.ask_ostutor(question)


# ---------------- translation ----------------

def _sources(chunks):
    out, seen = [], set()
    for c in chunks or []:
        module, page = c.get("module"), c.get("page")
        if module in (None, "Unknown") and page in (None, "Unknown"):
            continue
        key = (str(module), str(page))
        if key in seen:
            continue
        seen.add(key)
        src = {}
        if module not in (None, "Unknown"):
            src["module"] = str(module)
        if page not in (None, "Unknown"):
            src["page"] = page if isinstance(page, (int, str)) else str(page)
        out.append(src)
    return out


def _theory(result):
    answer = result["answer"]
    sources = [] if answer == NOT_AVAILABLE else _sources(result.get("chunks"))
    return {"type": "theory", "answer": answer, "sources": sources}


def _numerical(outcome):
    parsed = outcome["parsed"]
    if len(outcome["results"]) != 1:
        names = ", ".join(numerical._ALGO_NAMES.get(k, k) for k in parsed.algorithms)
        return {
            "type": "needs_input",
            "message": f"Your question asks for several algorithms ({names}). "
                       "Please ask for one scheduling algorithm at a time.",
        }
    key, res = parsed.algorithms[0], outcome["results"][0]
    processes = []
    for p in parsed.processes:
        item = {"id": p.pid, "arrival_time": p.arrival, "burst_time": p.burst}
        if p.priority is not None:
            item["priority"] = p.priority
        processes.append(item)
    order = {p.pid: i for i, p in enumerate(parsed.processes)}
    explanation = (
        numerical._explain_one(key, res, parsed.processes)
        + "\n\nFormulas used: Turnaround (TAT) = Completion (CT) - Arrival; "
          "Waiting (WT) = Turnaround - Burst."
    )
    inp = {"processes": processes}
    if res.quantum is not None:
        inp["time_quantum"] = res.quantum
    return {
        "type": "numerical",
        "algorithm": res.algorithm,
        "input": inp,
        "gantt_chart": [{"process": pid, "start": s, "end": e} for pid, s, e in res.gantt],
        "process_results": [
            {"id": r.pid, "completion_time": r.completion,
             "turnaround_time": r.turnaround, "waiting_time": r.waiting}
            for r in sorted(res.processes, key=lambda x: order[x.pid])
        ],
        "average_waiting_time": res.avg_waiting,
        "average_turnaround_time": res.avg_turnaround,
        "explanation": explanation,
    }


def translate(result):
    if result["route"] == "theory":
        return _theory(result)
    status = result.get("status")
    if status == "solved":
        return _numerical(result["outcome"])
    if status in ("needs_input", "unsupported"):
        return {"type": status, "message": result["answer"]}
    return _err(result.get("answer") or "Something went wrong.")


@app.post("/api/ask")
def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        return _err("Please type a question.")
    try:
        result = numerical.answer_question(question, theory_fn=theory_fn)
    except rag.GeneratorBusy:
        return _err("The tutor is busy right now. Please try again shortly.")
    except RuntimeError as e:
        if not rag.LOADED:
            return _err("The tutor is still starting up, so theory questions can't be "
                        "answered yet. Numerical problems still work.")
        print("ask() failed:", type(e).__name__)
        return _err("The tutor couldn't write an answer right now. Please try again.")
    except Exception as e:  # never crash the API; question text is not logged
        print("ask() failed:", type(e).__name__)
        return _err("Something went wrong while answering this question.")
    return translate(result)


class QuizRequest(BaseModel):
    topic: str
    kind: str | None = None
    avoid: list[str] = []


@app.post("/api/quiz")
def make_quiz(req: QuizRequest):
    if req.topic not in quiz.TOPICS:
        return _err("Please pick one of the course topics.")
    try:
        return quiz.make_question(req.topic, req.kind, req.avoid)
    except rag.GeneratorBusy:
        return _err("The tutor is busy right now. Please try again shortly.")
    except RuntimeError:
        if not rag.LOADED:
            return _err("The tutor is still starting up. Please try again in a moment.")
        return _err("The tutor couldn't write a question right now. Please try again.")
    except Exception as e:
        print("quiz failed:", type(e).__name__)
        return _err("The tutor couldn't write a question from the course material. Please try again.")
