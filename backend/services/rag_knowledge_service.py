import logging
from config import TOP_K
from services.query_builder import build_query

logger = logging.getLogger(__name__)


def retrieve_knowledge(findings, rag):

    logger.info("Retrieving knowledge using FAISS.")

    knowledge = []

    for finding in findings:

        query = build_query(finding)

        logger.info(f"Searching for: {query}")

        results = rag.search(query, k=TOP_K)

        for result in results:

            knowledge.append(result["text"])

    logger.info(f"Retrieved {len(knowledge)} chunks.")

    return knowledge