import logging

logger = logging.getLogger(__name__)


def retrieve_knowledge(findings, rag):

    logger.info("Retrieving knowledge using FAISS.")

    knowledge = []

    for finding in findings:

        query = (
            f"{finding['calculated_status']} "
            f"{finding['parameter']}"
        )

        logger.info(f"Searching for: {query}")

        results = rag.search(query, k=3)

        for result in results:

            knowledge.append(result["text"])

    logger.info(f"Retrieved {len(knowledge)} chunks.")

    return knowledge