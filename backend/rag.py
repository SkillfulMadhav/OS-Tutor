# ============================================================
#   OSTUTOR RAG (theory) -- ported from the Kaggle notebook.
#   Only change: model/data loading moved into load(), and the
#   data path comes from config.py. Everything below section 5b
#   (cleanup, retrieval, prompt, generation) is copied verbatim.
# ============================================================

import os
import pickle
import re
import unicodedata

import numpy as np
import faiss
import wordninja
from spellchecker import SpellChecker

import config

# Populated by load()
chunks = None
embeddings = None
index = None
embedding_model = None
tokenizer = None
model = None
non_latin_token_ids = []
LOADED = False
LOAD_ERROR = None


def load():
    """Load RAG artifacts, embedding model and Qwen once at startup."""
    global chunks, embeddings, index, embedding_model, tokenizer, model
    global non_latin_token_ids, LOADED, LOAD_ERROR
    try:
        SAVE_DIR = config.RAG_DATA_DIR
        print("RAG data directory:", SAVE_DIR)
        print("Files:", os.listdir(SAVE_DIR))

        with open(os.path.join(SAVE_DIR, "chunks.pkl"), "rb") as f:
            chunks = pickle.load(f)
        embeddings = np.load(os.path.join(SAVE_DIR, "embeddings.npy"))
        index = faiss.read_index(os.path.join(SAVE_DIR, "faiss.index"))
        print("Chunks loaded:", len(chunks))
        print("FAISS vectors:", index.ntotal, "dim:", index.d)

        if config.GENERATOR == "groq":
            # CPU-only hosting: same BGE model via ONNX, answers written by Groq.
            from fastembed import TextEmbedding
            if not config.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY is not set")
            embedding_model = TextEmbedding(config.EMBED_MODEL, cache_dir=config.FASTEMBED_CACHE, threads=1)
            print("Embedding model loaded (fastembed):", config.EMBED_MODEL)
            LOADED = True
            print("OSTUTOR READY (generator: groq,", config.GROQ_MODEL + ")")
            return

        import torch
        from sentence_transformers import SentenceTransformer
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

        embedding_model = SentenceTransformer(config.EMBED_MODEL)
        print("Embedding model loaded:", config.EMBED_MODEL)

        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(
            config.MODEL_NAME, quantization_config=quantization_config, device_map="auto"
        )
        print(f"{config.MODEL_NAME} loaded in 4-bit!")

        # 5b. Non-Latin token suppression list
        special_ids = set(tokenizer.all_special_ids)
        ids = []
        for tok_str, tok_id in tokenizer.get_vocab().items():
            if tok_id in special_ids:
                continue
            decoded = tokenizer.convert_tokens_to_string([tok_str])
            if decoded and _is_non_english_text(decoded):
                ids.append(tok_id)
        non_latin_token_ids = ids
        print(f"Suppressing {len(ids)} non-Latin tokens at generation time.")
        LOADED = True
        print("OSTUTOR READY")
    except Exception as e:  # server keeps running; numericals still work
        LOAD_ERROR = f"{type(e).__name__}: {e}"
        print("OSTUTOR THEORY MODEL FAILED TO LOAD:", LOAD_ERROR)


# torch is needed inside ask_ostutor (torch.no_grad)
try:
    import torch
except ImportError:  # pragma: no cover
    torch = None


def _is_non_english_text(s):
    """True if s contains an alphabetic char outside plain ASCII a-z/A-Z.

    This catches not just CJK/Devanagari/Cyrillic/Arabic scripts, but also
    diacritic Latin letters used by Vietnamese, Spanish, Indonesian, etc.
    (e.g. 'ủ', 'á', 'ầ') which are technically Unicode-named "LATIN" and
    would slip past a script-name-based check.
    """
    for ch in s:
        if ch.isalpha() and not ch.isascii():
            return True
    return False

# ============================================================
# 5c. MERGED-WORD REPAIR (dictionary-aware, whitelist-scoped)
# ============================================================
#
# Design notes:
#
# 1. wordninja's own internal word list (`_wordcost`) is NOT a real
#    dictionary -- it's a segmentation cost table with ~125k entries
#    that includes tons of short junk fragments and abbreviations
#    (needed for its DP algorithm to work at all). Treating membership
#    in it as "is this a real word" is unreliable.
#
# 2. pyspellchecker is used instead as the real-word validity source.
#    We only need ONE fragment in a group to register as invalid to
#    trigger a repair attempt; we don't rely on it to catch everything
#    alone.
#
# 3. Corrections (turning a suspicious fragment into a real word) are
#    scoped ONLY to TECH_WHITELIST (our own curated course vocabulary),
#    never a general dictionary. A general-dictionary fuzzy match is
#    unpredictable (e.g. "procesfor" is edit-distance-1 from BOTH
#    "processor" and other unrelated real words). Restricting to our
#    own known vocabulary avoids this class of false positive entirely.
#
# 4. pyspellchecker occasionally recognizes rare/archaic real words
#    that coincidentally match a corrupted merge ("astatic" is a real
#    but obscure physics term; "betaken" is archaic past-participle
#    of "betake"; "Ina"/"Asa" are names; "fora" is the plural of
#    "forum"). These slip past the dictionary-word guard and are
#    handled individually via RESIDUAL_FIXES below rather than a
#    general frequency-based filter, since a wider automated fix would
#    add complexity beyond what's currently needed.
# ============================================================

TECH_WHITELIST = {
    "fcfs", "sjf", "rr", "cpu", "cpus", "os", "api", "apis", "posix",
    "mmu", "io", "gpu", "win32", "java", "tlb", "ram", "rom",
    "process", "processes", "processor", "thread", "threads",
    "semaphore", "semaphores", "deadlock", "deadlocks", "paging",
    "segmentation", "scheduling", "priority", "virtualization",
    "preemptive", "nonpreemptive", "noncontiguous", "contiguous",
    "multiprogramming", "multitasking", "multithreading",
    "synchronization", "fragmentation", "interrupt", "interrupts",
    "kernel", "filesystem", "algorithm", "algorithms", "physical",
    "logical", "hardware", "software", "interface", "throughput",
    "concurrency", "concurrent", "asynchronous", "synchronous",
    "decrement", "decrements", "decrementing",
    "increment", "increments", "incrementing",
    "multilevel", "starvation", "aging",
}

_word_token_re = re.compile(r"^([^\w]*)([\w'-]*)([^\w]*)$")

_SHORT_REAL_WORDS = {
    "a", "i", "of", "to", "in", "on", "at", "is", "as",
    "or", "if", "be", "by", "it", "an", "do", "no", "so",
    "up", "we", "he", "my", "us", "am", "go", "me"
}

_BAD_SPLIT_FRAGMENTS = {
    "ing", "ed", "er", "es", "tion", "ers", "ely",
    "ive", "ity", "ous", "ment", "ally", "est", "re",
    "dec", "men"
}

_SPELL = SpellChecker()
_SPELL.word_frequency.load_words(TECH_WHITELIST)


def _is_dictionary_word(word):
    low = word.lower()
    if low in _BAD_SPLIT_FRAGMENTS:
        return False
    if low in TECH_WHITELIST or low in _SHORT_REAL_WORDS:
        return True
    if len(low) < 3:
        return False
    return low in _SPELL


def _edit_distance_one_or_less(a, b):
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 1:
        return 2
    if len(a) != len(b):
        longer, shorter = (a, b) if len(a) > len(b) else (b, a)
        i = j = edits = 0
        while i < len(longer) and j < len(shorter):
            if longer[i] != shorter[j]:
                edits += 1
                i += 1
                if edits > 1:
                    return 2
            else:
                i += 1
                j += 1
        return 1
    diffs = sum(x != y for x, y in zip(a, b))
    return diffs if diffs <= 1 else 2


def _dictionary_correction(word):
    low = word.lower()
    if _is_dictionary_word(low):
        return low
    best = None
    for term in TECH_WHITELIST:
        if abs(len(term) - len(low)) <= 1 and _edit_distance_one_or_less(low, term) <= 1:
            if best is None or len(term) > len(best):
                best = term
    return best


def _repair_invalid_parts(parts):
    if not parts:
        return None

    result = []
    i = 0

    while i < len(parts):
        current = parts[i].lower()

        if _is_dictionary_word(current):
            result.append(parts[i])
            i += 1
            continue

        joined = current
        j = i + 1
        while j < len(parts) and not _is_dictionary_word(parts[j]):
            joined += parts[j].lower()
            j += 1

        corrected = _dictionary_correction(joined)
        if corrected is not None and len(corrected) >= 4:
            result.append(corrected)
            i = j
            continue

        if result:
            combined = result[-1].lower() + joined
            corrected = _dictionary_correction(combined)
            if (
                corrected is not None
                and len(corrected) >= 4
                and corrected != result[-1].lower()
            ):
                result[-1] = corrected
                i = j
                continue

        # Third: try joining the invalid run with the NEXT fragment too
        # (e.g. "al" + "locator" -> "allocator"), in case that fragment,
        # though individually valid-looking on its own, is actually
        # part of the same corrupted word.
        if j < len(parts):
            combined_next = joined + parts[j].lower()
            corrected = _dictionary_correction(combined_next)
            if (
                corrected is not None
                and len(corrected) >= 4
                and corrected != parts[j].lower()
            ):
                result.append(corrected)
                i = j + 1
                continue

        return None

    return result


def _split_core(core, min_len=3):
    low = core.lower()

    if _is_dictionary_word(low):
        return core

    parts = core.split("-")
    fixed_parts = []
    changed = False

    for part in parts:
        part_low = part.lower()
        if (
            len(part) >= min_len
            and part.isalpha()
            and part_low not in TECH_WHITELIST
        ):
            segmented = list(wordninja.split(part))
            repaired = _repair_invalid_parts(segmented)
            if repaired is not None:
                repaired_text = " ".join(repaired)
                if repaired_text.lower() != part_low:
                    fixed_parts.append(repaired_text)
                    changed = True
                    continue
        fixed_parts.append(part)

    return "-".join(fixed_parts) if changed else core


def fix_merged_words(text):
    out_tokens = []
    for tok in text.split(" "):
        m = _word_token_re.match(tok)
        if not m:
            out_tokens.append(tok)
            continue
        prefix, core, suffix = m.groups()
        out_tokens.append(prefix + _split_core(core) + suffix)
    return " ".join(out_tokens)


def _whitelist_correction(word):
    low = word.lower()
    if low in TECH_WHITELIST:
        return low
    best = None
    for term in TECH_WHITELIST:
        if abs(len(term) - len(low)) <= 1 and _edit_distance_one_or_less(low, term) <= 1:
            if best is None or len(term) > len(best):
                best = term
    return best


_FRAGMENT_TOKEN_RE = re.compile(r"^([^a-zA-Z]*)([a-zA-Z]+)([^a-zA-Z]*)$")


def fix_fragmented_words(text):
    """
    Rejoin suspicious space-separated fragments when their
    concatenation fuzzy-matches a known course term, e.g.:
        "pro ces" -> "process"
        "se mph ores" -> "semaphores"
        "che du ling" -> "scheduling"
    """
    tokens = text.split()
    result = []
    i = 0

    while i < len(tokens):
        found = False

        for span in range(2, 5):
            if i + span > len(tokens):
                continue

            group = tokens[i:i + span]
            cores, prefix, suffix, ok = [], "", "", True

            for idx, t in enumerate(group):
                m = _FRAGMENT_TOKEN_RE.match(t)
                if not m:
                    ok = False
                    break
                p, core, s = m.groups()
                if idx == 0:
                    prefix = p
                if idx == len(group) - 1:
                    suffix = s
                elif p or s:
                    ok = False
                    break
                cores.append(core)

            if not ok:
                continue

            joined = "".join(cores).lower()

            # Accept an EXACT dictionary match first -- this is safe
            # because there's no ambiguity (the concatenation IS a real
            # word, e.g. "num"+"ber" -> "number", "Mult"+"i"+"level" ->
            # "multilevel"). Fuzzy correction (edit distance) is what
            # needs to stay scoped to TECH_WHITELIST only -- see design
            # note 3 above -- since a fuzzy match against the general
            # dictionary is what caused false positives like
            # "procesfor" -> "processor" (swallowing "for").
            if _is_dictionary_word(joined):
                result.append(prefix + joined + suffix)
                i += span
                found = True
                break

            corrected = _whitelist_correction(joined)

            if corrected:
                result.append(prefix + corrected + suffix)
                i += span
                found = True
                break

        if not found:
            result.append(tokens[i])
            i += 1

    return " ".join(result)


def fix_word_typos(text):
    """
    Correct a standalone (already-spaced) misspelled word against
    TECH_WHITELIST, e.g. "semphores" -> "semaphores", "multileavel"
    -> "multilevel". This is separate from fix_fragmented_words/
    fix_merged_words -- those handle merged or split tokens, this
    handles a single whole token that's just misspelled by one
    character.
    """
    def fix(m):
        w = m.group(0)
        low = w.lower()
        if low in TECH_WHITELIST or low in _SPELL:
            return w
        best = None
        for term in TECH_WHITELIST:
            if abs(len(term) - len(low)) <= 1 and _edit_distance_one_or_less(low, term) <= 1:
                if best is None or len(term) > len(best):
                    best = term
        if best:
            return best[0].upper() + best[1:] if w[0].isupper() else best
        return w

    return re.sub(r"[A-Za-z]{5,}", fix, text)


# ============================================================
# 5d. OTHER CLEANUP HELPERS
# ============================================================

_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]+")


def strip_non_latin(text):
    return _NON_ASCII_RE.sub("", text)


def strip_markdown_lists(text):
    """Strip bullet/numbered list markers line-by-line.

    Only EXPLICITLY bullet-marked lines ("-", "*", "1.") get a period
    appended before joining -- this is what fixes a real bulleted list
    like "- A page number\\n- A page offset" collapsing into unreadable
    "A page number A page offset".

    Plain line breaks with NO bullet marker are just space-joined with
    no inserted punctuation, since we can't reliably tell "new
    sentence" from "mid-sentence line wrap" for an unmarked line
    break -- the safe choice is to insert nothing rather than guess
    wrong.
    """
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        is_bullet = bool(re.match(r"^[ \t]*[-*\u2022]\s+", line)) or \
            bool(re.match(r"^[ \t]*\d+[.)]\s+", line))
        line = re.sub(r"^[ \t]*[-*\u2022]\s+", "", line)
        line = re.sub(r"^[ \t]*\d+[.)]\s+", "", line)
        line = line.strip()
        if not line:
            continue
        if is_bullet and line[-1] not in ".!?:":
            line += "."
        cleaned.append(line)
    return " ".join(cleaned)


def normalize_capitalization(text):
    """Fix pervasive random mid-sentence capitalization (e.g. "Process
    can become blocked when Performing a wait operation On semaphore").

    This is generation noise: the model appears to echo Title-Case
    styling from the retrieved slide-deck chunks into the middle of
    otherwise normal-case sentences. Lowercases every word except: the
    first word of each sentence, recognized short acronyms (all-caps,
    <=5 chars, e.g. CPU, TLB, FCFS), and a small list of proper nouns
    that are genuinely always capitalized (UNIX, Windows, Linux, etc).
    Runs BEFORE normalize_terminology, which re-establishes correct
    casing for known multi-word technical terms afterward.
    """
    known_proper_nouns = {"unix", "windows", "linux", "darwin", "macos"}
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    fixed_sentences = []

    for sent in sentences:
        words = sent.split(" ")
        new_words = []
        for idx, w in enumerate(words):
            m = re.match(r"^([\w'-]*)([^\w]*)$", w)
            core, punct = (m.group(1), m.group(2)) if m else (w, "")
            if not core:
                new_words.append(w)
                continue
            if core.isalpha() and core.upper() == core and len(core) <= 5:
                new_words.append(w)
                continue
            if core.lower() in known_proper_nouns:
                new_words.append(core.capitalize() + punct)
                continue
            if idx == 0:
                new_words.append(core[0].upper() + core[1:].lower() + punct)
                continue
            new_words.append(core.lower() + punct)
        fixed_sentences.append(" ".join(new_words))

    return " ".join(fixed_sentences)


# Small residual fixes for anomalies not caught by the general repair
# functions above (kept intentionally short).
RESIDUAL_FIXES = {
    "(MU)": "(MMU)",
    " MU ": " MMU ",
    "non-preemtive": "non-preemptive",
    "abstractings": "abstracting",
    "segreation": "segregation",
    "decremes": "decrements",
    "inexecution": "in execution",
    "are source": "a resource",
    "smalltime": "small time",
    # "astatic" and "betaken" are rare/archaic real words (a physics
    # term; the archaic past participle of "betake") that pyspell-
    # checker recognizes, which slips them past the merged-word repair
    # guard even though they're actually "a static"/"be taken" merged
    # with no space.
    "astatic": "a static",
    "betaken": "be taken",
    # "semiconductor" has no legitimate meaning anywhere in this course
    # material; the model has substituted it for "semaphore" at least
    # once, likely a phonetic/embedding-adjacent word confusion, same
    # class of error as the earlier "sourcing" -> "scheduling" fix.
    "semiconductor": "semaphore",
    # "overtime" is a real English word (extra work hours) that
    # coincidentally matches "over time" merged with no space -- same
    # pattern as "smalltime" above.
    "overtime": "over time",
}


def _fix_binary_semaphore_digit_error(text):
    """Fix "0 and 0" -> "0 and 1" for binary semaphore values.

    This is a rare model-generation digit substitution (not caught by
    any spacing/merge repair, since "0 and 0" is already correctly
    spaced and spelled -- just factually wrong). Safe to always
    correct: "0 and 0" has no legitimate meaning in this course
    material, since binary semaphore values are canonically 0 and 1.
    """
    return re.sub(r"\b0\s+and\s+0\b", "0 and 1", text)


def _fix_io_abbreviation(text):
    """"I. O." -> "I/O" -- the model sometimes writes the I/O
    abbreviation with dot-separated letters instead of a slash."""
    return re.sub(r"\bI\.\s*O\.", "I/O", text)


def _fix_await_operation(text):
    """"await operation" -> "a wait operation".

    "await" is a real, common English word, so it doesn't trip the
    merged-word repair guard the way "astatic"/"betaken" do -- but in
    this course's context, "await operation" always means the
    semaphore "wait" operation with the leading "a" swallowed, never
    the verb "await". Scoped to this specific phrase (not a blanket
    "await" -> "a wait" replacement) since "await" has legitimate
    standalone uses in English that must not be touched.
    """
    return re.sub(r"\bawait\s+operation\b", "a wait operation", text, flags=re.IGNORECASE)


_SCHEDULING_ALGO_LIST_MARKERS = [
    "Shortest Job First", "Priority Scheduling", "Round Robin",
    "Multilevel Queue Scheduling", "Multilevel Feedback Queue Scheduling",
]


def disambiguate_fcfs_in_list(text):
    """"First-Come, First-Served" has a comma inside its own name,
    which makes a comma-separated list of scheduling algorithms LOOK
    like it has one extra item when quickly counted or naively
    comma-split (a 6-algorithm list reads as 7 fragments because
    "First-Come" and "First-Served (FCFS)" get split apart by that
    internal comma). Only strips the internal comma when FCFS appears
    alongside at least one other algorithm name in the same sentence
    (i.e. it's part of an enumerated list) -- standalone mentions like
    "FCFS executes processes in arrival order" are untouched.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    fixed = []
    for sent in sentences:
        if "First-Come, First-Served" in sent and any(
            marker in sent for marker in _SCHEDULING_ALGO_LIST_MARKERS
        ):
            sent = sent.replace("First-Come, First-Served", "First-Come First-Served")
        fixed.append(sent)
    return " ".join(fixed)


_DANGLING_VERBS = {
    "maps", "consists", "results", "includes", "contains", "provides",
    "requires", "uses", "allows", "enables", "needs", "refers",
}


def drop_dangling_incomplete_sentence(text):
    """If the answer's last sentence ends immediately after a verb
    that virtually always requires a following object/complement
    (e.g. "The page table maps." with nothing after "maps"), the
    model most likely stopped generating mid-thought rather than
    completing the sentence. This slips past the existing incomplete-
    sentence check because the text DOES end in a period -- it just
    doesn't finish the thought. Drops that trailing sentence rather
    than presenting an incomplete claim as if it were finished.
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    if len(sentences) <= 1:
        return text
    last = sentences[-1]
    words = re.sub(r"[.!?]+$", "", last).split()
    last_word = words[-1].lower() if words else ""
    if last_word in _DANGLING_VERBS:
        return " ".join(sentences[:-1])
    return text


# Case-insensitive terminology normalization. Separator character
# classes include "." as well as whitespace/hyphen, so a stray period
# left mid-term by generation noise (e.g. "Shortest Job. First.")
# still gets recognized and corrected as a safety net.
TERMINOLOGY_PATTERNS = [
    (r"\bshortest\s+job[\s.\-]+next\b", "Shortest Job First"),
    (r"\bshortest\s+job[\s.\-]+first\b", "Shortest Job First"),
    # se(?:r)?v tolerates the "seved" typo (dropped r) as well as the
    # correctly-spelled "served"/"serve".
    (r"\bfirst[\s.\-]*come[,\s.\-]*first[\s.\-]*se(?:r)?v(?:e|ed)\b",
     "First-Come, First-Served"),
    (r"\bpriority\s+scheduling\b", "Priority Scheduling"),
    (r"\bpriority\s+schedulers\b", "Priority Scheduling"),
    (r"\bcpu\s+scheduling\s+algorithms\b", "CPU scheduling algorithms"),
    (r"\bnon[\s.\-]+contiguous\b", "noncontiguous"),
    (r"\bnon[\s.\-]+preemptive\b", "non-preemptive"),
    (r"\bmulti\s+taking\b", "multitasking"),
    (r"\bmultitaskings\b", "Multitasking"),
    (r"\bmultilevelqueue\s+scheduling\b", "Multilevel Queue Scheduling"),
    (r"\bmultilevelfeedback\s+queue\s+scheduling\b",
     "Multilevel Feedback Queue Scheduling"),
    (r"\bmultilevel\s+feedback\s+queue\s+scheduling\b",
     "Multilevel Feedback Queue Scheduling"),
    (r"\bmultilevel\s+queue\s+scheduling\b", "Multilevel Queue Scheduling"),
    (r"\bmulti[\s.\-]+level[\s.\-]+feedback[\s.\-]+queue[\s.\-]+scheduling\b",
     "Multilevel Feedback Queue Scheduling"),
    (r"\bmulti[\s.\-]+level[\s.\-]+queue[\s.\-]+scheduling\b",
     "Multilevel Queue Scheduling"),
    (r"\bround[\s.\-]+robin\b", "Round Robin"),
    (r"\bcpus\b", "CPUs"),
    (r"\bfsfs\b", "FCFS"),
    # "sourcing" is never a legitimate term in this course material --
    # the model has substituted it for "Scheduling" at least twice
    # ("Priority Sourcing", "multilevel queue sourcing"). General fix
    # instead of patching each specific phrase separately.
    (r"\bsourcing\b", "Scheduling"),
    (r"(First-Come, First-Served)\s*\([A-Za-z]+\)", r"\1 (FCFS)"),
    (r"(Shortest Job First)\s*\([A-Za-z]+\)", r"\1 (SJF)"),
    (r"(Round Robin)\s*\([A-Za-z]+\)", r"\1 (RR)"),
    (r"(First-Come, First-Served)\s+FCFS\b", r"\1 (FCFS)"),
    (r"(Shortest Job First)\s+SJF\b", r"\1 (SJF)"),
    (r"(Round Robin)\s+RR\b", r"\1 (RR)"),
    (
        r"(First-Come, First-Served\s*\(FCFS\))\s+"
        r"(Shortest Job First\s*\(SJF\))\s+and\s+"
        r"(Priority Scheduling)",
        r"\1, \2, and \3"
    ),
    (
        r"(?i)monolithic structure\s+layered approach\s+microkernels\s+"
        r"modules\s+and\s+hybrid systems",
        "Monolithic Structure, Layered Approach, Microkernels, Modules, "
        "and Hybrid Systems"
    ),
]


def normalize_terminology(text):
    for pattern, replacement in TERMINOLOGY_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def collapse_duplicate_words(text):
    return re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)


_NON_TERMINAL_WORDS = {
    "multiple", "several", "various", "different", "many", "other",
    "some", "each", "every", "same", "certain", "both", "few",
    "most", "more", "less", "these", "those", "such",
    "the", "a", "an",
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten",
    "equal", "wait", "performs", "consists",
    # Common prepositions that can never end a declarative sentence
    # (all OS-tutor answers are declarative, never questions, so this
    # is safe): "convenient to. Use" -> "convenient to use".
    "to", "of", "for", "with", "by", "from", "into", "onto", "about",
}


def fix_spurious_mid_sentence_periods(text):
    """Fix a stray period the model sometimes inserts mid-sentence
    (e.g. "switches between multiple. Tasks at regular intervals").

    This must run BEFORE truncate_sentences/normalize_capitalization,
    since those both split on sentence-ending punctuation -- left
    uncorrected, the fragment after a stray period gets treated as a
    genuine new sentence and its capitalization gets preserved/
    reinforced rather than fixed.

    Only fires when the word immediately before the period is one that
    can never grammatically end a declarative sentence on its own
    (determiner, quantifier, number, or preposition) -- this keeps it
    safe from ever touching a genuine sentence boundary.
    """
    def repl(m):
        word_before, rest = m.group(1), m.group(2)
        if word_before.lower() in _NON_TERMINAL_WORDS:
            return word_before + " " + rest[0].lower() + rest[1:]
        return m.group(0)
    return re.sub(r"\b(\w+)\.\s+([A-Z]\w*)", repl, text)


_COMMON_PREFIX_BEFORE_A = {
    "in", "has", "as", "for", "is", "was", "on", "at", "by", "of",
    "with", "to", "be", "had", "have", "were", "this", "that", "do"
}


def fix_trailing_a_merge(text):
    """Fix the very common 'word'+'a' merge pattern: "hasa" -> "has a",
    "ina" -> "in a", "asa" -> "as a", "fora" -> "for a".

    These slip past the general merged-word repair because pyspell-
    checker coincidentally recognizes some of them as rare real words
    or proper names ("Ina", "Asa" are names; "fora" is the plural of
    "forum"), which triggers _split_core's early "already a valid
    word, don't touch it" guard before any split is even attempted.
    Only rewrites when the part before the trailing "a" is one of a
    small curated list of common short words that frequently precede
    "a" in English -- this is what keeps "banana", "data", "area",
    etc. safe from being touched.
    """
    def fix(m):
        word = m.group(0)
        prefix = word[:-1]
        if prefix.lower() in _COMMON_PREFIX_BEFORE_A:
            return prefix + " a"
        return word
    return re.sub(r"\b[a-zA-Z]+a\b", fix, text)

def drop_numerical_example_sentences(text, question):
    """If the question has no process data, remove any sentence that
    smuggles in a worked example (P1, P2, ... or Gantt values)."""
    if re.search(r"\bp\d+\b", question, re.IGNORECASE):
        return text
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    kept = [s for s in sentences
            if not re.search(r"\bp\d+\b", s, re.IGNORECASE)
            and not re.search(r"\bgantt\b.*\d", s, re.IGNORECASE)]
    if not kept:
        return "That information is not available in the provided course material."
    return " ".join(kept)



def truncate_sentences(text, max_sentences):
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    if len(sentences) > max_sentences:
        text = " ".join(sentences[:max_sentences])
    return text


def merge_short_sentence_fragments(text, min_words=3):
    """Safety net against severe generation degeneration where the
    model fragments what should be one sentence into a run of
    nonsensical 1-2 word 'sentences' (e.g. "a page. Offset." or
    "Page table. The. Page table contains the."), typically seen when
    generation runs long and the model resorts to inserting spurious
    periods. Merges any suspiciously short "sentence" back into the
    one before it (as a continuation, not a new sentence) rather than
    leaving it as a broken standalone fragment.
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    if not sentences:
        return text
    merged = [sentences[0]]
    for s in sentences[1:]:
        word_count = len(s.rstrip(".!?").split())
        if word_count < min_words:
            prev = merged[-1]
            if prev and prev[-1] in ".!?":
                prev = prev[:-1]
            frag = s[0].lower() + s[1:] if s else s
            merged[-1] = prev + " " + frag
        else:
            merged.append(s)
    return " ".join(merged)


def _strip_glued_bullet_prefix(word):
    if len(word) < 4:
        return word
    first = word[0].lower()
    if first not in ("q", "v"):
        return word
    rest = word[1:]
    if not rest.isalpha():
        return word
    original_split = wordninja.split(word.lower())
    rest_split = wordninja.split(rest.lower())
    if (
        len(rest_split) == 1
        and rest_split[0] == rest.lower()
        and len(original_split) > 1
    ):
        return rest
    return word


def clean_chunk_text(text):
    text = text.replace("\u00a7", ".")
    text = re.sub(r"(?<=\s)[qv](?=\s)", "", text)
    text = re.sub(r"^[qv]\s+", "", text)
    text = " ".join(_strip_glued_bullet_prefix(w) for w in text.split(" "))
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ============================================================
# 5e. RETRIEVAL-LAYER FIXES
# ============================================================
#
# Diagnosed via direct inspection of actual retrieval results against
# three known failure cases:
#
# 1. Junk chunks: syllabus pages and bare title slides (e.g. "BCSE303L
#    -Operating Systems Syllabus") sometimes rank in the top 10 by
#    embedding similarity despite carrying zero substantive content,
#    displacing genuinely relevant chunks.
#
# 2. Multi-concept questions: a single embedding of "Explain TLB,
#    cache memory, demand paging, and starvation" gravitates entirely
#    toward whichever concept dominates semantically, so the other
#    concepts' chunks may never be retrieved at all.
#
# 3. Topic-qualified questions: "starvation in CPU scheduling" can
#    rank a starvation chunk from an unrelated module above the
#    actually-relevant CPU-scheduling content, because pure semantic
#    search matches on the word "starvation" without respecting the
#    "in CPU scheduling" qualifier.
# ============================================================

_JUNK_CHUNK_PATTERNS = [
    r"^\s*(BCSE\S*\s*[-\u2013]?\s*)?(operating systems?\s*)?syllabus\b",
    r"^\s*(BCSE\S*\s*[-\u2013]?\s*)?text and reference books?\b",
    r"^\s*module\s*\d+\s*[-\u2013\u2014]\s*[\w\s]+$",
]


def _is_junk_chunk(text):
    """Filter out navigational/metadata chunks (syllabus pages, bare
    title-only slides) that carry no substantive content."""
    stripped = text.strip()
    if len(stripped) < 25:
        return True
    for pattern in _JUNK_CHUNK_PATTERNS:
        if re.search(pattern, stripped, re.IGNORECASE):
            return True
    return False

def _is_numerical_example_chunk(text):
    """Worked-example slides (process tables, Gantt charts with P1/P2/P3
    and numbers). Useful for numerical questions, but they contaminate
    theory answers."""
    t = text.lower()
    if len(re.findall(r"\bp\d+\b", t)) >= 3:
        return True
    if "gantt" in t and len(re.findall(r"\d+", t)) >= 6:
        return True
    return False


def _embed_text(text):
    if config.GENERATOR == "groq":  # fastembed ONNX build of the same BGE model
        v = np.asarray(list(embedding_model.embed([text])), dtype="float32")
        return v / np.linalg.norm(v, axis=1, keepdims=True)
    return embedding_model.encode(
        [text], convert_to_numpy=True, normalize_embeddings=True
    ).astype("float32")


class GeneratorBusy(Exception):
    """Groq rate limit reached."""


def _groq_generate(messages):
    import requests
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
        json={
            "model": config.GROQ_MODEL,
            "messages": messages,
            "max_tokens": 180,
            "temperature": 0,
            "reasoning_effort": "none",
        },
        timeout=60,
    )
    if r.status_code == 429:
        raise GeneratorBusy()
    if r.status_code >= 400:
        raise RuntimeError(f"Groq HTTP {r.status_code}")
    return (r.json()["choices"][0]["message"]["content"] or "").strip()


def _mmr_select(candidate_items, want_k, lambda_param=0.7):
    """Greedily select a diverse subset via Maximal Marginal Relevance,
    using the precomputed chunk embeddings (loaded as `embeddings`).
    Balances relevance (score) against redundancy with what's already
    selected -- this is what stops several near-duplicate chunks about
    one sub-topic from crowding out coverage of other sub-topics.
    """
    if len(candidate_items) <= want_k:
        return candidate_items

    pool = sorted(candidate_items, key=lambda x: -x[1])
    selected = [pool.pop(0)]

    while len(selected) < want_k and pool:
        best_i, best_mmr = None, -1e9
        for i, (idx, score) in enumerate(pool):
            sim_to_selected = max(
                float(np.dot(embeddings[idx], embeddings[sel_idx]))
                for sel_idx, _ in selected
            )
            mmr = lambda_param * score - (1 - lambda_param) * sim_to_selected
            if mmr > best_mmr:
                best_mmr, best_i = mmr, i
        selected.append(pool.pop(best_i))

    return selected


def retrieve_for_question(question, top_k, all_course_concepts, diversify=False):
    """Retrieve chunk indices for a question. Worked-example chunks are
    skipped (they leak P1/P2 tables into theory answers) unless almost
    nothing else was found."""
    question_lower = question.lower()

    mentioned = [
        c for c in all_course_concepts
        if re.search(rf"\b{re.escape(c)}\b", question_lower)
    ]

    candidates = {}
    skipped_examples = {}

    def add(scores, indices, weight=1.0):
        for score, idx in zip(scores, indices):
            if idx < 0 or idx >= len(chunks):
                continue
            if _is_junk_chunk(chunks[idx]["text"]):
                continue
            weighted = float(score) * weight
            if _is_numerical_example_chunk(chunks[idx]["text"]):
                skipped_examples[idx] = max(skipped_examples.get(idx, 0), weighted)
                continue
            if idx not in candidates or weighted > candidates[idx]:
                candidates[idx] = weighted

    pool_k = top_k * 3 if diversify else top_k * 2

    if len(mentioned) >= 2:
        per_concept_k = max(3, pool_k // len(mentioned))
        for concept in mentioned:
            scores, indices = index.search(_embed_text(concept), per_concept_k)
            add(scores[0], indices[0])
        scores, indices = index.search(_embed_text(question), pool_k)
        add(scores[0], indices[0], weight=0.85)
    else:
        scores, indices = index.search(_embed_text(question), pool_k)
        add(scores[0], indices[0])

        if mentioned:
            concept = mentioned[0]
            qualifiers = [
                c for c in all_course_concepts
                if c != concept and re.search(rf"\b{re.escape(c)}\b", question_lower)
            ]
            if qualifiers:
                for idx in list(candidates.keys()):
                    text_lower = chunks[idx]["text"].lower()
                    if concept in text_lower and any(q in text_lower for q in qualifiers):
                        candidates[idx] *= 1.15

    # Don't starve the answer if almost everything was a worked example
    if len(candidates) < 2:
        candidates.update(skipped_examples)

    items = list(candidates.items())
    if diversify:
        selected = _mmr_select(items, top_k)
    else:
        selected = sorted(items, key=lambda kv: -kv[1])[:top_k]

    return [(idx, score) for idx, score in selected]


# ============================================================
# 6. OSTUTOR RAG FUNCTION
# ============================================================

def ask_ostutor(question, top_k=None):

    # ========================================================
    # 0. COURSE CONCEPTS (used for broad-detection, retrieval, and
    #    the grounding check below -- defined once, up front, so
    #    retrieve_for_question's multi-concept/keyword-boost logic
    #    and the grounding check stay in sync with the same list)
    # ========================================================

    course_concepts = [
        "operating system", "process", "thread", "system call",
        "cpu scheduling", "fcfs", "first-come, first-served",
        "sjf", "shortest job first", "priority scheduling",
        "round robin", "multilevel queue", "multilevel feedback queue",
        "semaphore", "deadlock", "paging", "page table",
        "segmentation", "virtualization", "virtual machine",
        "disk architecture", "multiprogramming", "multitasking",
        "synchronization", "starvation", "aging", "tlb",
        "cache memory", "demand paging", "context switch",
        "critical section", "mutex",
    ]

    # ========================================================
    # 1. ADAPTIVE TOP-K
    # ========================================================

    question_lower = question.lower()

    broad_terms = [
        "all", "different", "types", "algorithms", "compare",
        "comparison", "difference", "differences", "explain the",
        "list", "main", "major", "important",
    ]

    # Word-boundary matching prevents SUBSTRING false positives (e.g.
    # "main" inside "domain"), but it does NOT prevent "main" matching
    # as its own complete word in a phrase like "What is main memory?"
    # -- that's a genuine OS term, not an indicator of a broad/list
    # question, so it's excluded specifically below.
    is_broad = any(
        re.search(rf"\b{re.escape(term)}\b", question_lower)
        for term in broad_terms
    )

    # "main memory" (and "primary memory") are specific OS terms, not
    # signals that the question wants a broad/list-style answer. If
    # "main" is the only reason is_broad tripped, recheck without it --
    # but keep is_broad True if some OTHER genuine broad_terms keyword
    # also matched (e.g. "algorithms" in "the main CPU scheduling
    # algorithms" -- that question SHOULD still get broad treatment).
    if is_broad and re.search(r"\bmain\s+memory\b", question_lower):
        _other_terms = [t for t in broad_terms if t != "main"]
        is_broad = any(
            re.search(rf"\b{re.escape(term)}\b", question_lower)
            for term in _other_terms
        )

    # Also treat as broad/multi-part if the question names 2+ distinct
    # course concepts (e.g. "Explain multiprogramming and multitasking
    # clearly"), even when it matches none of the broad_terms keywords
    # above. Without this, such questions get the tight 2-sentence cap
    # and the model drops the second topic entirely to fit. Reuses
    # course_concepts (defined above) rather than a separate list, so
    # this stays in sync with what retrieve_for_question treats as a
    # "named concept" for multi-concept retrieval.
    _topic_hits = sum(
        1 for c in course_concepts
        if re.search(rf"\b{re.escape(c)}\b", question_lower)
    )
    if _topic_hits >= 2:
        is_broad = True

    if top_k is None:
        top_k = 10 if is_broad else 5

    # ========================================================
    # 2-3. RETRIEVE (multi-concept-aware, junk-filtered, with
    #    keyword-boosted re-ranking for topic-qualified questions,
    #    and MMR diversification for broad questions -- see
    #    retrieve_for_question / section 5e for full rationale)
    # ========================================================

    ranked_results = retrieve_for_question(
        question, top_k, course_concepts, diversify=is_broad
    )

    retrieved_chunks = []
    for idx, score in ranked_results:
        retrieved_chunks.append({
            "text": chunks[idx]["text"],
            "module": chunks[idx].get("module", "Unknown"),
            "page": chunks[idx].get("page", "Unknown"),
            "score": score
        })

    # ========================================================
    # 4. BUILD CONTEXT
    # ========================================================

    context = "\n\n".join(
        f"[Module {c['module']} | Page {c['page']}]\n{clean_chunk_text(c['text'])}"
        for c in retrieved_chunks
    )

    # ========================================================
    # 5. COURSE MATERIAL GROUNDING CHECK
    # ========================================================

    context_lower = context.lower()

    mentioned_concepts = [c for c in course_concepts if c in question_lower]
    missing_concepts = [c for c in mentioned_concepts if c not in context_lower]

    # ========================================================
    # 6. HARD GROUNDING FOR COMPARISON QUESTIONS
    # ========================================================

    comparison_question = any(
        phrase in question_lower
        for phrase in [
            "difference between", "differences between", "compare",
            "comparison between", "compare and contrast"
        ]
    )

    if comparison_question and missing_concepts:
        return (
            "That information is not available in the provided course material.",
            retrieved_chunks
        )

    # ========================================================
    # 7. HARD GROUNDING FOR DIRECT CONCEPT QUESTIONS
    # ========================================================

    if mentioned_concepts and missing_concepts:
        return (
            "That information is not available in the provided course material.",
            retrieved_chunks
        )

    # ========================================================
    # 8. SYSTEM MESSAGE
    # ========================================================

    system_message = """You are OSTutor, an Operating Systems tutor.

IMPORTANT LANGUAGE RULE:
- Answer ONLY in clear standard English.
- Do not use Chinese, Japanese, Korean, Hindi, or any other language.
- Do not mix languages.
- Use normal spaces between every word.
- Do not merge words together.
- Do not remove spaces from phrases.
- Do not put individual words on separate lines.

FORMATTING RULE:
- Write in plain flowing sentences only.
- Do not use bullet points, numbered lists, headings, or markdown
  formatting of any kind (no "-", "*", "#", "**", underscores as
  word separators).
- Do not use underscores in place of spaces between words.

SOURCE RULE:
- Answer the user's question using ONLY the provided course material.
- Do not use outside knowledge.
- Do not add facts from your pretrained knowledge.
- Do not assume information that is not present in the course material.
- If a proper noun, acronym, or API/OS name is not explicitly stated
  in the course material, do not include it.
- The retrieved course material may include content from a different
  but similarly-named topic (e.g. disk scheduling appearing alongside
  CPU scheduling). Stay strictly on the topic the question asks about.
  Never substitute or blend terminology from a different topic, even
  if it appears in the retrieved material.

NO WORKED EXAMPLES RULE:
- Never include worked numerical examples, sample process tables, Gantt
  charts, or specific process names and values (such as P1, P2, burst
  times, arrival times) in your answer.
- If the question asks how something is calculated, give only the general
  formula or rule stated in the course material, never a worked example.

CONCISENESS RULE:
- Give a direct, minimal answer to exactly what was asked.
- Do not add extra background, extra mechanisms, or extra examples
  beyond what is needed to directly answer the question.
- If the question asks "What is X", give only the definition —
  do not also describe related mechanisms unless asked.
- For definition questions, do not provide examples, applications,
  classifications, implementation details, or related concepts unless
  they are part of the definition explicitly stated in the course material.
- Do not continue the answer with additional facts after the definition.
- Stop answering once the question has been directly answered.

STRICT RULES:
- Give ONLY the answer.
- Do not show reasoning or internal thoughts.
- Do not discuss how you found the answer.
- Do not repeat the answer.
- Do not write "Final Answer".
- Do not mention the sources unless the user asks.
- Preserve the terminology used in the course material.
- Do not abbreviate or alter terminology from the course material.
- Preserve numeric values, thresholds, and conditions exactly as stated
  in the course material (e.g. "the value is zero", "greater than 0").
  Do not approximate, round, or alter them.
- If the answer is not supported by the course material, say exactly:

"That information is not available in the provided course material."

- If the question asks for multiple items (types, algorithms, structures,
  etc.), scan the ENTIRE provided course material for every relevant item
  before answering. Do not stop after finding only some of them.
- Do not invent additional items.
- If the question implies a specific number of items (e.g. "the three
  types of X") but the course material supports a different number,
  do NOT invent or pad an item to match that number. Instead, state
  plainly how many the material actually supports and list only those,
  e.g. "The course material describes two types: A and B." rather than
  inventing a third.
- A general descriptive sentence about the overall concept (e.g. "X is
  a variable used to coordinate processes") is NOT itself a named type
  or category, even if the question's wording implies more items exist
  than the material actually names. Only count something as a distinct
  "type" if the material explicitly names and describes it as one.
  For example: if a question asks for "the three types of X" but the
  material only names two specific types (A and B) and separately just
  describes X in general terms, the correct answer lists only A and B
  -- it does not turn the general description into a fabricated third
  type.
- If a question's wording assumes a count of items (e.g. "the three
  types of X") that the course material does not support, your answer
  MUST explicitly state the actual count instead of silently listing
  items to match the assumed number. Use this exact pattern: "The
  course material describes [actual number] types of X: [list them].
  It does not describe a third type." Do not just list items without
  addressing the mismatch.
- For comparison questions, only compare concepts supported by the provided material.
- When a "compare" question names or implies multiple categories (e.g.
  "compare the different operating system structures"), address EVERY
  relevant category the material supports, even briefly, rather than
  elaborating in depth on only one of them. Breadth across all the
  named categories matters more than depth on a single one.

The course material is the ONLY source of truth.
"""

    # ========================================================
    # 9. USER MESSAGE
    # ========================================================

    user_message = f"""COURSE MATERIAL:

{context}

QUESTION:

{question}

Answer ONLY the question.

Give a short, direct answer.
For questions asking for multiple items, include every relevant item explicitly supported by the course material, even if this requires more than 3 sentences.
For simple definition questions, keep the answer to 1-3 sentences.
Use only information explicitly stated in the course material.
Use clear standard English.
Use normal spaces between every word.
Do not merge words.
Do not put individual words on separate lines.
Do not repeat information.
Do not add information from outside the course material.
"""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

    # ========================================================
    # 10. QWEN3 CHAT TEMPLATE (THINKING DISABLED)
    # ========================================================

    if config.GENERATOR == "groq":
        answer = _groq_generate(messages)
    else:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )

        # ========================================================
        # 11. TOKENIZE
        # ========================================================

        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        # ========================================================
        # 12. GENERATE
        # ========================================================

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=180,
                do_sample=False,
                repetition_penalty=1.0,          # was 1.05
                # no_repeat_ngram_size removed   # was 6
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
                suppress_tokens=non_latin_token_ids if non_latin_token_ids else None,
            )
        # ========================================================
        # 13. DECODE ONLY NEW TOKENS
        # ========================================================

        generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        answer = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

    # ========================================================
    # 14. REMOVE THINKING TAGS FIRST
    # ========================================================

    if "<think>" in answer:
        if "</think>" in answer:
            answer = answer.split("</think>", 1)[1].strip()
        else:
            answer = answer.replace("<think>", "").strip()


    # Cut anything after the model starts inventing a new chat turn
    for marker in ("</think>", "<|im_start|>", "<|im_end|>",
                   "\nhuman:", "\nuser:", "\nassistant:",
                   " human:", " user:", " assistant:"):
        pos = answer.lower().find(marker.lower())
        if pos > 0:
            answer = answer[:pos].strip()
    # ========================================================
    # 15. STRIP NON-LATIN + MARKDOWN LISTS
    # ========================================================

    answer = strip_non_latin(answer)
    answer = strip_markdown_lists(answer)

    # ========================================================
    # 16. NORMALIZE WHITESPACE
    # ========================================================

    answer = answer.replace("\t", " ")
    answer = " ".join(answer.split()).strip()

    answer = re.sub(r"(?<=[a-zA-Z])(?=[0-9])", " ", answer)
    answer = re.sub(r"(?<=[0-9])(?=[a-zA-Z])", " ", answer)
    answer = re.sub(r"(?<=[a-zA-Z])_(?=[a-zA-Z])", " ", answer)

    # ========================================================
    # 17. REPAIR MERGED / FRAGMENTED / MISSPELLED WORDS
    # ========================================================

    answer = fix_merged_words(answer)
    answer = fix_fragmented_words(answer)
    answer = fix_word_typos(answer)
    answer = fix_trailing_a_merge(answer)
    answer = _fix_io_abbreviation(answer)
    answer = _fix_await_operation(answer)
    answer = _fix_binary_semaphore_digit_error(answer)

    # ========================================================
    # 18. RESIDUAL FIXES + DUPLICATE WORD COLLAPSE
    # ========================================================

    for wrong, correct in RESIDUAL_FIXES.items():
        answer = answer.replace(wrong, correct)

    answer = collapse_duplicate_words(answer)
    answer = fix_spurious_mid_sentence_periods(answer)

    # ========================================================
    # 19. FIX SPACING AROUND PUNCTUATION
    # ========================================================

    answer = re.sub(r"\s+([,.!?;:])", r"\1", answer)
    answer = re.sub(r"\(\s+", "(", answer)
    answer = re.sub(r"\s+\)", ")", answer)
    answer = re.sub(r"([,.;:])(?=[A-Za-z])", r"\1 ", answer)
    answer = re.sub(r"(?<=[A-Za-z0-9])\(", r" (", answer)

    # ========================================================
    # 20. NORMALIZE CAPITALIZATION + TERMINOLOGY
    # ========================================================

    answer = normalize_capitalization(answer)
    answer = normalize_terminology(answer)
    answer = disambiguate_fcfs_in_list(answer)

    # ========================================================
    # 21. TRUNCATE OVER-GENERATION
    # ========================================================
    answer = drop_numerical_example_sentences(answer, question)
    max_sentences = 6 if (is_broad or comparison_question) else 2
    answer = merge_short_sentence_fragments(answer)
    answer = truncate_sentences(answer, max_sentences)

    if answer and answer[-1] not in ".!?":
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s]
        if len(sentences) > 1:
            answer = " ".join(sentences[:-1])

    answer = drop_dangling_incomplete_sentence(answer)

    # ========================================================
    # 22. REMOVE ACCIDENTAL TRAILING CHARACTERS
    # ========================================================

    answer = answer.rstrip("|").strip()

    # ========================================================
    # 23. EXACT FALLBACK WORDING
    # ========================================================

    if "That information is not available" in answer:
        answer = "That information is not available in the provided course material."

    # ========================================================
    # 24. FINAL WHITESPACE NORMALIZATION
    # ========================================================

    answer = " ".join(answer.split()).strip()

    return answer, retrieved_chunks
