"""Evaluation questions generated only from the course material.

Retrieves course chunks for a topic, asks the generator for ONE question
(multiple choice or true/false) that is answerable from those chunks, and
validates the result strictly. Anything malformed is rejected, never patched.
"""
import json
import random
import re

import config
import rag

TOPICS = {
    "Processes", "Threads", "System Calls", "CPU Scheduling", "Process Synchronization",
    "Semaphores", "Deadlocks", "Memory Management", "Paging", "Segmentation",
    "Virtual Memory", "TLB", "Disk Scheduling", "File Systems", "Virtualization",
}

SYSTEM = (
    "You write exam questions for an Operating Systems course. Use ONLY facts stated in the "
    "provided course material. Never use outside knowledge. Reply with JSON only."
)


KEYWORDS = {
    "Processes": ["process"], "Threads": ["thread"], "System Calls": ["system call"],
    "CPU Scheduling": ["scheduling", "scheduler"], "Process Synchronization": ["synchroniz", "critical section"],
    "Semaphores": ["semaphore"], "Deadlocks": ["deadlock"], "Memory Management": ["memory"],
    "Paging": ["paging", "page table", "frame"], "Segmentation": ["segment"],
    "Virtual Memory": ["virtual memory", "demand paging", "page replacement"], "TLB": ["tlb", "translation look"],
    "Disk Scheduling": ["disk"], "File Systems": ["file"], "Virtualization": ["virtual machine", "virtualiz", "hypervisor"],
}


def _context(topic):
    keys = KEYWORDS.get(topic, [topic.lower()])
    hits = rag.retrieve_for_question(topic, 10, [])
    on_topic = [h for h in hits if any(k in rag.chunks[h[0]]["text"].lower() for k in keys)]
    pool = (on_topic or hits)[:6]
    picked = random.sample(pool, min(3, len(pool)))
    parts, sources = [], []
    for idx, _ in picked:
        c = rag.chunks[idx]
        parts.append(rag.clean_chunk_text(c["text"])[:1200])
        sources.append({"module": c.get("module"), "page": c.get("page")})
    return "\n\n---\n\n".join(parts), sources


def _prompt(topic, kind, context, avoid):
    if kind == "mcq":
        shape = ('{"question": "...", "options": ["A", "B", "C", "D"], "answer_index": 0, '
                 '"explanation": "one or two sentences from the material"}')
        rule = "Exactly 4 short options, exactly one correct."
    else:
        shape = ('{"question": "a statement to judge", "options": ["True", "False"], '
                 '"answer_index": 0, "explanation": "one or two sentences from the material"}')
        rule = ("The question is a single statement; options are exactly [\"True\", \"False\"]. "
                f"Make the statement {random.choice(['true', 'false'])} according to the material.")
    avoid_txt = ""
    if avoid:
        avoid_txt = "\nDo not repeat these questions:\n" + "\n".join(f"- {a[:200]}" for a in avoid[:10])
    return (
        f"Course material:\n{context}\n\n"
        f"Write ONE {('multiple-choice' if kind == 'mcq' else 'true/false')} question about {topic}. "
        f"{rule} It must be answerable from the course material above. No numerical calculations."
        f"{avoid_txt}\n\nReturn JSON exactly in this shape:\n{shape}"
    )


def _generate(messages):
    import requests
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
        json={
            "model": config.GROQ_MODEL,
            "messages": messages,
            "max_tokens": 400,
            "temperature": 0.7,
            "reasoning_effort": "none",
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    if r.status_code == 429:
        raise rag.GeneratorBusy()
    if r.status_code >= 400:
        print("quiz groq error", r.status_code, r.text[:300])
        raise RuntimeError(f"Groq HTTP {r.status_code}")
    return r.json()["choices"][0]["message"]["content"] or ""


def _validate(raw, kind):
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip()).strip()
    data = json.loads(text)
    q = str(data.get("question", "")).strip()
    opts = data.get("options")
    ans = data.get("answer_index")
    expl = str(data.get("explanation", "")).strip()
    if not q or not isinstance(opts, list) or not isinstance(ans, int):
        raise ValueError("bad shape")
    opts = [str(o).strip() for o in opts]
    want = 4 if kind == "mcq" else 2
    if len(opts) != want or any(not o for o in opts) or len(set(o.lower() for o in opts)) != want:
        raise ValueError("bad options")
    if kind == "tf" and [o.lower() for o in opts] != ["true", "false"]:
        raise ValueError("bad tf options")
    if not 0 <= ans < want:
        raise ValueError("bad answer")
    return {"question": q, "options": opts, "answer_index": ans, "explanation": expl}


def make_question(topic, kind=None, avoid=None):
    if config.GENERATOR != "groq":
        raise RuntimeError("quiz requires the groq generator")
    if not rag.LOADED:
        raise RuntimeError("theory model not loaded")
    kind = kind if kind in ("mcq", "tf") else random.choice(["mcq", "mcq", "tf"])
    last = None
    for _ in range(2):
        context, sources = _context(topic)
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": _prompt(topic, kind, context, avoid or [])},
        ]
        try:
            item = _validate(_generate(messages), kind)
        except (ValueError, json.JSONDecodeError) as e:
            last = e
            continue
        clean_sources, seen = [], set()
        for s in sources:
            key = (str(s["module"]), str(s["page"]))
            if key in seen or (s["module"] in (None, "Unknown") and s["page"] in (None, "Unknown")):
                continue
            seen.add(key)
            src = {}
            if s["module"] not in (None, "Unknown"):
                src["module"] = str(s["module"])
            if s["page"] not in (None, "Unknown"):
                src["page"] = s["page"] if isinstance(s["page"], (int, str)) else str(s["page"])
            clean_sources.append(src)
        return {"type": "question", "topic": topic, "kind": kind, **item, "sources": clean_sources}
    raise ValueError(f"could not build a valid question: {last}")
