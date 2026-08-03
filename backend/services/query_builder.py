import logging

logger = logging.getLogger(__name__)


def build_query(finding):

    query = (
        f"{finding['parameter']} "
        f"{finding['calculated_status']} "
        f"meaning causes symptoms treatment diet"
    )

    logger.info(f"Generated query: {query}")

    return query