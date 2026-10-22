# ============================================================
#   OSTUTOR NUMERICAL MODULE  (paste into its OWN Kaggle cell)
#   Deterministic CPU-scheduling solvers + question router.
#   Needs no GPU, no model, and no extra pip installs.
#
#   Usage (after your main OSTUTOR cell has run):
#       result = answer_question(question, theory_fn=ask_ostutor)
#       print(result['answer'])
# ============================================================

# ============================================================
# DETERMINISTIC CPU SCHEDULING SOLVERS
#
# These compute exact numerical results for the classic non-
# preemptive/preemptive scheduling algorithms using plain Python
# arithmetic -- never asking the LLM to do the calculation itself.
# The LLM's job (elsewhere) is only to EXPLAIN a result that has
# already been computed exactly here.
#
# Each solver takes a list of Process objects and returns a
# ScheduleResult: per-process start/completion/waiting/turnaround
# times, plus a step-by-step execution order (a "Gantt chart" as a
# list of (pid, start, end) slices) that the explanation layer can
# narrate without having to re-derive the schedule itself.
# ============================================================

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Process:
    pid: str
    arrival: float
    burst: float
    priority: Optional[float] = None  # lower number = higher priority

    def __post_init__(self):
        if self.arrival < 0:
            raise ValueError(f"{self.pid}: arrival time cannot be negative")
        if self.burst <= 0:
            raise ValueError(f"{self.pid}: burst time must be positive")


@dataclass
class ProcessResult:
    pid: str
    arrival: float
    burst: float
    start: float
    completion: float
    waiting: float
    turnaround: float


@dataclass
class ScheduleResult:
    algorithm: str
    quantum: Optional[float]
    gantt: List[tuple]  # list of (pid, start, end)
    processes: List[ProcessResult]
    avg_waiting: float
    avg_turnaround: float

    def summary_text(self):
        """A plain-text summary intended as grounding context for the
        LLM's explanation step -- NOT meant to be shown to the student
        verbatim, though it safely could be."""
        lines = [f"Algorithm: {self.algorithm}"]
        if self.quantum is not None:
            lines.append(f"Time quantum: {self.quantum}")
        lines.append("")
        lines.append("Execution order (Gantt chart):")
        lines.append(" | ".join(f"{pid}[{s}-{e}]" for pid, s, e in self.gantt))
        lines.append("")
        lines.append(f"{'PID':<5}{'Arrival':<10}{'Burst':<8}{'Start':<8}{'Completion':<12}{'Waiting':<10}{'Turnaround':<10}")
        for p in self.processes:
            start_display = "-" if p.start is None else p.start
            lines.append(
                f"{p.pid:<5}{p.arrival:<10}{p.burst:<8}{start_display:<8}"
                f"{p.completion:<12}{p.waiting:<10}{p.turnaround:<10}"
            )
        lines.append("")
        lines.append(f"Average waiting time: {self.avg_waiting:.2f}")
        lines.append(f"Average turnaround time: {self.avg_turnaround:.2f}")
        return "\n".join(lines)


def _validate_priority_processes(processes):
    for p in processes:
        if p.priority is None:
            raise ValueError(
                f"{p.pid}: priority scheduling requires a priority value "
                f"for every process"
            )


def fcfs(processes: List[Process]) -> ScheduleResult:
    """First-Come, First-Served: processes run strictly in arrival
    order (ties broken by original list order), each running to
    completion with no preemption."""
    order = sorted(processes, key=lambda p: (p.arrival, processes.index(p)))
    results = []
    gantt = []
    clock = 0.0
    for p in order:
        start = max(clock, p.arrival)
        end = start + p.burst
        gantt.append((p.pid, start, end))
        results.append(ProcessResult(
            pid=p.pid, arrival=p.arrival, burst=p.burst,
            start=start, completion=end,
            waiting=start - p.arrival, turnaround=end - p.arrival,
        ))
        clock = end
    return _finalize("FCFS", None, gantt, results)


def sjf_nonpreemptive(processes: List[Process]) -> ScheduleResult:
    """Shortest Job First (non-preemptive): whenever the CPU is free,
    among all processes that have arrived but not yet run, pick the
    one with the smallest burst time (ties broken by arrival time,
    then original list order)."""
    remaining = list(processes)
    results = []
    gantt = []
    clock = 0.0
    original_index = {p.pid: i for i, p in enumerate(processes)}

    while remaining:
        available = [p for p in remaining if p.arrival <= clock]
        if not available:
            # CPU idles until the next process arrives
            clock = min(p.arrival for p in remaining)
            available = [p for p in remaining if p.arrival <= clock]
        chosen = min(
            available,
            key=lambda p: (p.burst, p.arrival, original_index[p.pid])
        )
        start = clock
        end = start + chosen.burst
        gantt.append((chosen.pid, start, end))
        results.append(ProcessResult(
            pid=chosen.pid, arrival=chosen.arrival, burst=chosen.burst,
            start=start, completion=end,
            waiting=start - chosen.arrival, turnaround=end - chosen.arrival,
        ))
        clock = end
        remaining.remove(chosen)

    return _finalize("Shortest Job First (SJF, non-preemptive)", None, gantt, results)


def priority_nonpreemptive(processes: List[Process]) -> ScheduleResult:
    """Priority Scheduling (non-preemptive): whenever the CPU is free,
    among all arrived-but-not-yet-run processes, pick the one with the
    smallest priority NUMBER (smallest integer = highest priority,
    matching the course material's stated convention). Ties broken by
    arrival time, then original list order."""
    _validate_priority_processes(processes)
    remaining = list(processes)
    results = []
    gantt = []
    clock = 0.0
    original_index = {p.pid: i for i, p in enumerate(processes)}

    while remaining:
        available = [p for p in remaining if p.arrival <= clock]
        if not available:
            clock = min(p.arrival for p in remaining)
            available = [p for p in remaining if p.arrival <= clock]
        chosen = min(
            available,
            key=lambda p: (p.priority, p.arrival, original_index[p.pid])
        )
        start = clock
        end = start + chosen.burst
        gantt.append((chosen.pid, start, end))
        results.append(ProcessResult(
            pid=chosen.pid, arrival=chosen.arrival, burst=chosen.burst,
            start=start, completion=end,
            waiting=start - chosen.arrival, turnaround=end - chosen.arrival,
        ))
        clock = end
        remaining.remove(chosen)

    return _finalize("Priority Scheduling (non-preemptive)", None, gantt, results)


def round_robin(processes: List[Process], quantum: float) -> ScheduleResult:
    """Round Robin: each process gets at most `quantum` time units per
    turn in a circular ready queue. Newly-arrived processes are added
    to the queue before a just-preempted process is re-added (the
    standard convention), and multiple arrivals at the same instant
    are added in original list order."""
    if quantum <= 0:
        raise ValueError("quantum must be positive")

    original_index = {p.pid: i for i, p in enumerate(processes)}
    remaining_burst = {p.pid: p.burst for p in processes}
    by_pid = {p.pid: p for p in processes}

    not_yet_arrived = sorted(processes, key=lambda p: (p.arrival, original_index[p.pid]))
    queue = []
    gantt = []
    clock = 0.0
    completion = {}

    def admit_arrivals(up_to_time):
        nonlocal not_yet_arrived
        still_waiting = []
        for p in not_yet_arrived:
            if p.arrival <= up_to_time:
                queue.append(p.pid)
            else:
                still_waiting.append(p)
        not_yet_arrived = still_waiting

    # Prime the clock to the first arrival if nothing has arrived at t=0
    if not_yet_arrived and not_yet_arrived[0].arrival > 0:
        clock = not_yet_arrived[0].arrival
    admit_arrivals(clock)

    while queue or not_yet_arrived:
        if not queue:
            # CPU idles until the next arrival
            clock = not_yet_arrived[0].arrival
            admit_arrivals(clock)
            continue

        pid = queue.pop(0)
        run_time = min(quantum, remaining_burst[pid])
        start = clock
        end = start + run_time
        gantt.append((pid, start, end))
        remaining_burst[pid] -= run_time
        clock = end

        # Admit anyone who arrived during this slice BEFORE re-queuing
        # the just-run process (standard RR convention).
        admit_arrivals(clock)

        if remaining_burst[pid] > 0:
            queue.append(pid)
        else:
            completion[pid] = clock

    results = []
    for p in processes:
        end = completion[p.pid]
        results.append(ProcessResult(
            pid=p.pid, arrival=p.arrival, burst=p.burst,
            start=None, completion=end,  # RR has multiple starts; omit single start
            waiting=end - p.arrival - p.burst, turnaround=end - p.arrival,
        ))
    results.sort(key=lambda r: original_index[r.pid])

    return _finalize(f"Round Robin (quantum={quantum})", quantum, gantt, results)


def _with_idle(gantt):
    """Insert explicit IDLE slices wherever the CPU sits unused -- both
    a leading gap (first arrival > 0) and gaps between slices. Makes
    CPU idle time visible to the student instead of leaving it implied
    by a jump in the timeline."""
    out = []
    clock = 0.0
    for pid, start, end in gantt:
        if start > clock:
            out.append(("IDLE", clock, start))
        out.append((pid, start, end))
        clock = end
    return out


def _finalize(algorithm, quantum, gantt, results):
    gantt = _with_idle(gantt)
    avg_wait = sum(r.waiting for r in results) / len(results)
    avg_turnaround = sum(r.turnaround for r in results) / len(results)
    return ScheduleResult(
        algorithm=algorithm, quantum=quantum, gantt=gantt,
        processes=results, avg_waiting=avg_wait, avg_turnaround=avg_turnaround,
    )



# ============================================================
# QUESTION ROUTER + SCHEDULING PROBLEM PARSER
#
# Turns a free-text numerical question into solver inputs, and
# decides whether a question is THEORY (-> RAG) or NUMERICAL
# (-> deterministic solvers).
#
# Design principle: be conservative. A wrong parse produces a
# confidently wrong number, which is worse than asking the student
# to clarify -- so anything ambiguous returns a request for more
# information, and unsupported variants are refused explicitly
# rather than silently solved as a different algorithm.
#
# Supported input formats (arrival time, then burst time, then
# optional priority):
#   A) Tuples:      P1(0,5)  P2 (1, 3)  P3(2,8,2)
#   B) Keywords:    P1 arrival=0 burst=5 priority=2
#   C) Table rows:  optionally with a header naming the columns
#                   (column order is read from the header)
#   D) Lists:       Arrival times: 0,1,2  Burst times: 5,3,8
# ============================================================

import re
from dataclasses import dataclass, field
from typing import List, Optional


_NUM = r"\d+(?:\.\d+)?"
_PID = r"[Pp]\d+"


@dataclass
class ParsedProblem:
    algorithms: List[str] = field(default_factory=list)   # subset of fcfs/sjf/priority/rr
    processes: List[Process] = field(default_factory=list)
    quantum: Optional[float] = None
    problems: List[str] = field(default_factory=list)      # human-readable parse issues


# ------------------------------------------------------------
# Algorithm / quantum detection
# ------------------------------------------------------------

def detect_algorithms(text):
    """Return algorithm keys mentioned in the question, in order of
    first appearance."""
    t = text.lower()
    patterns = [
        ("rr",       r"\bround[\s-]*robin\b|\brr\b"),
        ("sjf",      r"\bshortest[\s-]*job[\s-]*(?:first|next)\b|\bsjf\b"),
        # "priority" alone is NOT enough: it's also a table column
        # header. Require it to be used as an algorithm name.
        ("priority", r"\bpriority\s+(?:scheduling|algorithm|based)\b"
                     r"|\b(?:using|with|by|under|apply|for)\s+priority\b"
                     r"|\bpriority\s+(?:non[\s-]?preemptive)\b"),
        ("fcfs",     r"\bfcfs\b|\bfirst[\s-]*come\b|\bfifo\b"),
    ]
    found = []
    for key, pat in patterns:
        m = re.search(pat, t)
        if m:
            found.append((m.start(), key))
    found.sort()
    return [k for _, k in found]


def detect_unsupported(text, algorithms):
    """Return a message if the question asks for a variant we don't
    solve exactly (so we refuse rather than answer the wrong
    algorithm), else None."""
    t = text.lower()
    if re.search(r"\bsrtf\b|shortest[\s-]+remaining", t):
        return ("Shortest Remaining Time First (preemptive SJF) is not supported yet. "
                "Currently supported: FCFS, SJF (non-preemptive), Priority "
                "(non-preemptive), and Round Robin.")
    preemptive = re.search(r"(?<!non-)(?<!non )(?<!non)\bpreemptive\b", t)
    if preemptive and ("sjf" in algorithms or "priority" in algorithms):
        return ("Preemptive SJF/Priority scheduling is not supported yet. "
                "Currently supported: FCFS, SJF (non-preemptive), Priority "
                "(non-preemptive), and Round Robin.")
    return None


def extract_quantum(text):
    t = text.lower()
    m = re.search(rf"(?:time\s*)?(?:quantum|slice)\s*(?:of|=|:|is)?\s*({_NUM})", t)
    if not m:
        m = re.search(rf"\bq\s*=\s*({_NUM})", t)
    return _num(m.group(1)) if m else None


def _strip_quantum_phrase(text):
    """Remove the quantum phrase so its number can't be mistaken for
    a process attribute by the table/list parsers."""
    text = re.sub(rf"(?i)(?:time\s*)?(?:quantum|slice)\s*(?:of|=|:|is)?\s*{_NUM}", " ", text)
    text = re.sub(rf"(?i)\bq\s*=\s*{_NUM}", " ", text)
    return text


# ------------------------------------------------------------
# Process-data parsing (formats A-D)
# ------------------------------------------------------------

def _num(s):
    v = float(s)
    return int(v) if v.is_integer() else v


def _parse_tuples(text):
    """Format A: P1(0,5) / P1 (0, 5) / P1(0,5,2) -> (arrival, burst[, priority])."""
    out = []
    for m in re.finditer(
        rf"\b({_PID})\s*\(\s*({_NUM})\s*,\s*({_NUM})(?:\s*,\s*({_NUM}))?\s*\)", text
    ):
        pid = m.group(1).upper()
        pri = _num(m.group(4)) if m.group(4) is not None else None
        out.append(Process(pid, _num(m.group(2)), _num(m.group(3)), pri))
    return out


def _parse_keywords(text):
    """Format B: each process id followed by arrival=/burst=/priority= values."""
    matches = list(re.finditer(rf"\b({_PID})\b", text))
    if not matches:
        return []
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        seg = text[m.end():end]
        arr = re.search(rf"(?i)\b(?:arrival(?:\s*time)?|at)\b\D{{0,12}}?({_NUM})", seg)
        bur = re.search(rf"(?i)\b(?:burst(?:\s*time)?|bt|cpu\s*burst)\b\D{{0,12}}?({_NUM})", seg)
        pri = re.search(rf"(?i)\bpriority\b\D{{0,12}}?({_NUM})", seg)
        if arr and bur:
            out.append(Process(
                m.group(1).upper(), _num(arr.group(1)), _num(bur.group(1)),
                _num(pri.group(1)) if pri else None,
            ))
    return out


def _parse_lists(text):
    """Format D: 'Arrival times: 0,1,2  Burst times: 5,3,8 [Priorities: ...]'."""
    def grab(label_pat):
        m = re.search(rf"(?i){label_pat}\s*[:=]?\s*[\[\(]?\s*({_NUM}(?:\s*[,\s]\s*{_NUM})*)", text)
        return [_num(x) for x in re.findall(_NUM, m.group(1))] if m else None

    arrivals = grab(r"arrival(?:\s*times?)?")
    bursts = grab(r"burst(?:\s*times?)?")
    priorities = grab(r"priorit(?:y|ies)")
    if arrivals is None or bursts is None:
        return []
    if len(arrivals) != len(bursts):
        raise ValueError(
            f"{len(arrivals)} arrival times but {len(bursts)} burst times were given."
        )
    if priorities is not None and len(priorities) != len(bursts):
        raise ValueError(
            f"{len(priorities)} priorities but {len(bursts)} burst times were given."
        )
    return [
        Process(f"P{i + 1}", arrivals[i], bursts[i],
                priorities[i] if priorities else None)
        for i in range(len(bursts))
    ]


def _parse_table(text):
    """Format C: rows like 'P1 0 5' or 'P1 0 5 2'. If a header line names
    the columns, the column order is read from it."""
    order = ["arrival", "burst", "priority"]   # default column order
    for line in re.split(r"[\n;]", text):
        if re.search(_PID, line):
            continue
        low = line.lower()
        positions = {}
        for key, pat in (("arrival", r"arrival|\bat\b"), ("burst", r"burst|\bbt\b"),
                         ("priority", r"priority")):
            m = re.search(pat, low)
            if m:
                positions[key] = m.start()
        if "burst" in positions:     # a usable header
            order = [k for k, _ in sorted(positions.items(), key=lambda kv: kv[1])]
            break

    out = []
    for line in re.split(r"[\n;]", text):
        m = re.match(
            rf"^\s*({_PID})[\s,|\t:]+({_NUM})(?:[\s,|\t]+({_NUM}))?(?:[\s,|\t]+({_NUM}))?\s*[.]?\s*$",
            line,
        )
        if not m:
            continue
        values = [_num(g) for g in m.groups()[1:] if g is not None]
        if len(values) < len(order) and "arrival" not in order:
            pass
        fields = dict(zip(order, values))
        if "burst" not in fields:
            continue
        if "arrival" not in order and len(values) == len(order):
            fields["arrival"] = 0      # header had no arrival column
        if "arrival" not in fields:
            # headerless 2-number row: (arrival, burst)
            fields = dict(zip(["arrival", "burst", "priority"], values))
        out.append(Process(
            m.group(1).upper(), fields["arrival"], fields["burst"], fields.get("priority"),
        ))
    return out


def parse_scheduling_problem(question):
    parsed = ParsedProblem()
    parsed.algorithms = detect_algorithms(question)
    parsed.quantum = extract_quantum(question)
    cleaned = _strip_quantum_phrase(question)

    try:
        procs = _parse_tuples(cleaned) or _parse_keywords(cleaned) \
            or _parse_lists(cleaned) or _parse_table(cleaned)
    except ValueError as e:
        parsed.problems.append(str(e))
        return parsed

    # Reject duplicate process ids -- a sign the parse went wrong.
    seen = set()
    for p in procs:
        if p.pid in seen:
            parsed.problems.append(f"Process {p.pid} appears more than once.")
        seen.add(p.pid)
    parsed.processes = procs
    return parsed


# ------------------------------------------------------------
# Router
# ------------------------------------------------------------

_CALC_VERB = r"\b(calculate|compute|determine|solve|work\s*out|find|draw)\b"
_METRIC = r"waiting\s*time|turn\s*around\s*time|turnaround|completion\s*time|response\s*time|gantt"


_THEORY_CUES = (r"\b(how|what|why|when|which|explain|define|describe|formula|formulae|"
                r"meaning|difference|differences|steps|procedure|concept)\b")


_DEFINITIONAL_CUES = r"\b(formula|formulae|define|definition|meaning|difference|differences|concept)\b"

_IMPERATIVE_START = (r"^\s*(?:please\s+|pls\s+|can you\s+|could you\s+)?"
                     r"(?:calculate|compute|solve|determine|find|work\s*out|draw)\b")


def route_question(question):
    """Return 'numerical', 'numerical_incomplete', or 'theory'.

    - numerical:            process data was parsed
    - numerical_incomplete: the student wants something calculated/solved
                            (names an algorithm or metric) but gave no
                            usable data -> solver replies with needs_input
    - theory:               everything else ("What is FCFS?", "Explain FCFS",
                            "How is waiting time calculated?")
    """
    parsed = parse_scheduling_problem(question)
    if parsed.processes:
        return "numerical"

    q = question.lower()
    names_algo = bool(detect_algorithms(q))
    names_metric = bool(re.search(_METRIC, q))
    if not (names_algo or names_metric):
        return "theory"

    # "formula / define / difference ..." is always a theory question
    if re.search(_DEFINITIONAL_CUES, q):
        return "theory"

    # Starts with a command: "Calculate FCFS", "Solve round robin",
    # "Find waiting time using FCFS" -> numerical, even with no data
    if re.match(_IMPERATIVE_START, q):
        return "numerical_incomplete"

    # Command verb somewhere else, but no question wording
    if re.search(_CALC_VERB, q) and not re.search(_THEORY_CUES, q):
        return "numerical_incomplete"

    return "theory"
# ------------------------------------------------------------
# Solve + render
# ------------------------------------------------------------

_SOLVERS = {
    "fcfs": lambda procs, q: fcfs(procs),
    "sjf": lambda procs, q: sjf_nonpreemptive(procs),
    "priority": lambda procs, q: priority_nonpreemptive(procs),
    "rr": lambda procs, q: round_robin(procs, q),
}

_ALGO_NAMES = {
    "fcfs": "FCFS", "sjf": "SJF (non-preemptive)",
    "priority": "Priority (non-preemptive)", "rr": "Round Robin",
}

INPUT_FORMAT_HELP = (
    "I couldn't read the process data from your question. Please give it in a form like:\n"
    "  P1(0,5)  P2(1,3)  P3(2,8)          <- (arrival time, burst time)\n"
    "  P1(0,5,2) P2(1,3,1)                <- add a priority as a third value if needed\n"
    "or:  Arrival times: 0,1,2  Burst times: 5,3,8\n"
    "For Round Robin also state the time quantum, e.g. 'quantum = 2'."
)


def solve_scheduling_question(question):
    """Returns a dict:
        status:  'solved' | 'needs_input' | 'unsupported' | 'error'
        message: text to show the student when status != 'solved'
        parsed:  ParsedProblem (always present)
        results: list[ScheduleResult] (only when solved)
    """
    parsed = parse_scheduling_problem(question)

    if parsed.problems:
        return {"status": "error", "parsed": parsed,
                "message": "There's a problem with the data: " + " ".join(parsed.problems)}

    unsupported = detect_unsupported(question, parsed.algorithms)
    if unsupported:
        return {"status": "unsupported", "parsed": parsed, "message": unsupported}

    if not parsed.processes:
        return {"status": "needs_input", "parsed": parsed, "message": INPUT_FORMAT_HELP}

    if not parsed.algorithms:
        return {"status": "needs_input", "parsed": parsed,
                "message": "Which algorithm should I use? I can solve FCFS, SJF "
                           "(non-preemptive), Priority (non-preemptive), and Round Robin."}

    if "rr" in parsed.algorithms and parsed.quantum is None:
        return {"status": "needs_input", "parsed": parsed,
                "message": "Round Robin needs a time quantum. Please state it, "
                           "e.g. 'quantum = 2'."}
    if "priority" in parsed.algorithms and any(p.priority is None for p in parsed.processes):
        return {"status": "needs_input", "parsed": parsed,
                "message": "Priority Scheduling needs a priority value for every process. "
                    "Please give it as a third value, e.g. P1(0,5,2) P2(1,3,1) P3(2,4,3). "
                    "A smaller number means higher priority."}

    results = []
    try:
        for key in parsed.algorithms:
            results.append(_SOLVERS[key](parsed.processes, parsed.quantum))
    except ValueError as e:
        return {"status": "error", "parsed": parsed, "message": str(e)}

    return {"status": "solved", "parsed": parsed, "results": results, "message": ""}


def _fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.2f}"


def render_solution(outcome):
    """Plain-text rendering of a solve_scheduling_question outcome.
    Echoes the parsed input first so a misread is visible to the student."""
    if outcome["status"] != "solved":
        return outcome["message"]

    parsed = outcome["parsed"]
    has_priority = any(p.priority is not None for p in parsed.processes)

    lines = ["Here is how I read your problem:"]
    for p in parsed.processes:
        extra = f", priority {_fmt(p.priority)}" if p.priority is not None else ""
        lines.append(f"  {p.pid}: arrival {_fmt(p.arrival)}, burst {_fmt(p.burst)}{extra}")
    if parsed.quantum is not None and "rr" in parsed.algorithms:
        lines.append(f"  Time quantum: {_fmt(parsed.quantum)}")
    lines.append("")

    for res in outcome["results"]:
        lines.append(f"=== {res.algorithm} ===")
        lines.append("Gantt chart:")
        lines.append("  " + " | ".join(
            f"{pid} [{_fmt(s)}-{_fmt(e)}]" for pid, s, e in res.gantt))
        lines.append("")
        lines.append(f"  {'Process':<9}{'Completion':<12}{'Turnaround':<12}{'Waiting':<9}")
        order = {p.pid: i for i, p in enumerate(parsed.processes)}
        for r in sorted(res.processes, key=lambda x: order[x.pid]):
            lines.append(
                f"  {r.pid:<9}{_fmt(r.completion):<12}{_fmt(r.turnaround):<12}{_fmt(r.waiting):<9}")
        lines.append("")
        lines.append(f"  Average waiting time    = {res.avg_waiting:.2f}")
        lines.append(f"  Average turnaround time = {res.avg_turnaround:.2f}")
        lines.append("")
    lines.append("Formulas used: Turnaround = Completion - Arrival; "
                 "Waiting = Turnaround - Burst.")
    return "\n".join(lines).rstrip()
def render_full_solution(outcome):
    """One non-repeating answer: reading -> per algorithm (Gantt, steps,
    working, averages) -> formulas."""
    if outcome["status"] != "solved":
        return outcome["message"]

    parsed = outcome["parsed"]
    lines = ["Here is how I read your problem:"]
    for p in parsed.processes:
        extra = f", priority {_fmt(p.priority)}" if p.priority is not None else ""
        lines.append(f"  {p.pid}: arrival {_fmt(p.arrival)}, burst {_fmt(p.burst)}{extra}")
    if parsed.quantum is not None and "rr" in parsed.algorithms:
        lines.append(f"  Time quantum: {_fmt(parsed.quantum)}")
    lines.append("")

    for key, res in zip(parsed.algorithms, outcome["results"]):
        lines.append(f"=== {res.algorithm} ===")
        lines.append("Gantt chart:")
        lines.append("  " + " | ".join(
            f"{pid} [{_fmt(s)}-{_fmt(e)}]" for pid, s, e in res.gantt))
        lines.append("")
        lines.append(_explain_one(key, res, parsed.processes))
        lines.append("")

    lines.append("Formulas used: Turnaround (TAT) = Completion (CT) - Arrival; "
                 "Waiting (WT) = Turnaround - Burst.")
    return "\n".join(lines).rstrip()
# ============================================================
# QWEN EXPLANATION LAYER FOR NUMERICAL RESULTS
# ============================================================

# ============================================================
# DETERMINISTIC EXPLANATION LAYER (replaces the Qwen explainer)
# Every number comes from the solver result, so it can't be wrong.
# ============================================================

_CRITERION = {"sjf": ("burst", "smallest burst time"),
              "priority": ("priority", "smallest priority number (= highest priority)")}


def _explain_one(key, res, procs):
    L = []
    pmap = {p.pid: p for p in procs}
    done = set()
    remaining = {p.pid: p.burst for p in procs}

    L.append("How the schedule was built:")

    for pid, s, e in res.gantt:
        if pid == "IDLE":
            L.append(f"- {_fmt(s)} to {_fmt(e)}: CPU is idle (no process has arrived yet).")
            continue
        p = pmap[pid]

        if key == "fcfs":
            L.append(f"- t={_fmt(s)}: {pid} (arrived at {_fmt(p.arrival)}) is next in arrival order. "
                     f"It runs {_fmt(s)}-{_fmt(e)} to completion.")
            done.add(pid)

        elif key in _CRITERION:
            attr, rule = _CRITERION[key]
            ready = [q for q in procs if q.arrival <= s and q.pid not in done]
            if len(ready) == 1:
                why = f"only {pid} is ready"
            else:
                listing = ", ".join(f"{q.pid} ({attr} {_fmt(getattr(q, attr))})" for q in ready)
                why = f"ready: {listing}. Rule: pick the {rule}, so {pid}"
            L.append(f"- t={_fmt(s)}: {why}. It runs {_fmt(s)}-{_fmt(e)} without interruption.")
            done.add(pid)

        elif key == "rr":
            before = remaining[pid]
            remaining[pid] = before - (e - s)
            after = remaining[pid]
            if after > 0:
                L.append(f"- {_fmt(s)}-{_fmt(e)}: {pid} runs one quantum "
                         f"(remaining {_fmt(before)} -> {_fmt(after)}), then goes to the back of the queue.")
            else:
                L.append(f"- {_fmt(s)}-{_fmt(e)}: {pid} runs its last {_fmt(before)} unit(s) and finishes.")

    L.append("")
    L.append("Calculations (TAT = CT - Arrival, WT = TAT - Burst):")
    order = {p.pid: i for i, p in enumerate(procs)}
    rows = sorted(res.processes, key=lambda r: order[r.pid])
    for r in rows:
        L.append(f"- {r.pid}: CT = {_fmt(r.completion)}; "
                 f"TAT = {_fmt(r.completion)} - {_fmt(r.arrival)} = {_fmt(r.turnaround)}; "
                 f"WT = {_fmt(r.turnaround)} - {_fmt(r.burst)} = {_fmt(r.waiting)}")

    n = len(rows)
    wt_sum = " + ".join(_fmt(r.waiting) for r in rows)
    tat_sum = " + ".join(_fmt(r.turnaround) for r in rows)
    L.append("")
    L.append(f"- Average WT  = ({wt_sum}) / {n} = {res.avg_waiting:.2f}")
    L.append(f"- Average TAT = ({tat_sum}) / {n} = {res.avg_turnaround:.2f}")
    return "\n".join(L)


def explain_numerical_result(outcome):
    """Deterministic explanation built only from the solver result."""
    procs = outcome["parsed"].processes
    keys = outcome["parsed"].algorithms
    return "\n\n".join(
        _explain_one(k, res, procs) for k, res in zip(keys, outcome["results"])
    )


# ------------------------------------------------------------
# Top-level entry point
# ------------------------------------------------------------

def answer_question(question, theory_fn=None):
    """Theory -> existing RAG. Numerical -> exact solver + deterministic explanation."""
    route = route_question(question)

    if route == "theory":
        if theory_fn is None:
            return {"route": "theory", "answer": "[theory_fn not provided]"}
        answer, chunks_used = theory_fn(question)
        return {"route": "theory", "answer": answer, "chunks": chunks_used}

    outcome = solve_scheduling_question(question)

    if outcome["status"] != "solved":
        return {"route": route, "answer": outcome["message"],
                "status": outcome["status"], "outcome": outcome}

    return {
        "route": route,
        "answer": render_full_solution(outcome),
        "status": outcome["status"],
        "outcome": outcome,
    }