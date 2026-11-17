import logging
import threading

from config import TOP_K
from services.index_builder import build_index
from services.query_builder import build_query

logger = logging.getLogger(__name__)

_rag = None
_lock = threading.Lock()


def get_rag():
    """Build / load the FAISS index once and share it across the whole app."""

    global _rag

    if _rag is None:
        with _lock:
            if _rag is None:
                _rag = build_index()

    return _rag


def _with_source_tag(result) -> str:
    """The passage plus a short source tag, so the AI sees where it came from."""

    title = (result.get("source") or {}).get("title")

    return f"{result['text']}\n[Source: {title}]" if title else result["text"]


def _source_ref(result):

    source = result.get("source") or {}

    if not source.get("title"):
        return None

    return {
        "title": source["title"],
        "url": source.get("url", ""),
        "credit": source.get("credit", ""),
    }


def _collect(results_per_query):
    """Unique passages (with source tags) and unique source references, in order."""

    passages, sources = [], []
    seen_text, seen_source = set(), set()

    for results in results_per_query:
        for result in results:

            if result["text"] not in seen_text:
                seen_text.add(result["text"])
                passages.append(_with_source_tag(result))

            ref = _source_ref(result)

            if ref and ref["title"] not in seen_source:
                seen_source.add(ref["title"])
                sources.append(ref)

    return passages, sources


def retrieve_with_sources(findings):
    """Background knowledge for the *abnormal* findings, plus where it came from.
    Normal results do not need an explanation, and searching for them just
    pads the prompt with irrelevant text.

    Returns (passages, sources)."""

    rag = get_rag()

    searches = [
        rag.search(build_query(finding), k=TOP_K)
        for finding in findings
        if finding.get("calculated_status") != "Normal"
    ]

    passages, sources = _collect(searches)

    logger.info("Retrieved %d knowledge chunks from %d sources.", len(passages), len(sources))

    return passages, sources


def retrieve_knowledge(findings):

    return retrieve_with_sources(findings)[0]


def retrieve_for_question(question: str):
    """Retrieve knowledge relevant to a free-text chat question."""

    return _collect([get_rag().search(question, k=TOP_K)])[0]
