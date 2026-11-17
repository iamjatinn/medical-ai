import logging

logger = logging.getLogger(__name__)


def build_query(finding):

    query = (
        f"{finding['parameter']} "
        f"{finding['calculated_status']} "
        f"meaning causes symptoms treatment diet"
    )

    logger.debug("Generated query: %s", query)

    return query
