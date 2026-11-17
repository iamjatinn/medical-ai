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


def _unique(texts):

    seen = set()
    unique = []

    for text in texts:
        if text not in seen:
            seen.add(text)
            unique.append(text)

    return unique


def retrieve_knowledge(findings):
    """Retrieve background knowledge for the *abnormal* findings only.
    Normal results do not need an explanation, and searching for them just
    pads the prompt with irrelevant text."""

    rag = get_rag()

    knowledge = []

    for finding in findings:

        if finding.get("calculated_status") == "Normal":
            continue

        query = build_query(finding)

        for result in rag.search(query, k=TOP_K):
            knowledge.append(result["text"])

    knowledge = _unique(knowledge)

    logger.info("Retrieved %d knowledge chunks.", len(knowledge))

    return knowledge


def retrieve_for_question(question: str):
    """Retrieve knowledge relevant to a free-text chat question."""

    results = get_rag().search(question, k=TOP_K)

    return _unique(result["text"] for result in results)
