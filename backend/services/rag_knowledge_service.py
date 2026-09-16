import logging

from services.index_builder import build_index
from services.query_builder import build_query
from config import TOP_K

logger = logging.getLogger(__name__)

# Build/load the FAISS index once
rag = build_index()


def retrieve_knowledge(findings):

    logger.info("Retrieving knowledge using FAISS.")

    knowledge = []

    for finding in findings:

        query = build_query(finding)

        logger.info(f"Searching for: {query}")

        results = rag.search(query, k=TOP_K)

        for result in results:

            if isinstance(result, dict):
                knowledge.append(result["text"])
            else:
                knowledge.append(result)

    logger.info(f"Retrieved {len(knowledge)} knowledge chunks.")

    return knowledge