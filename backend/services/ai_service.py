import json
import logging

from prompts.report_prompt import REPORT_PROMPT
from services.gemini_service import generate_response
from services.rag_knowledge_service import retrieve_knowledge

logger = logging.getLogger(__name__)


def explain_report(findings):

    knowledge = retrieve_knowledge(findings)

    for number, chunk in enumerate(knowledge, start=1):
        logger.debug("Retrieved knowledge chunk %d: %s", number, chunk)

    report_data = {
        "findings": findings,
        "medical_knowledge": knowledge,
    }

    prompt = REPORT_PROMPT.format(report=json.dumps(report_data, indent=2))

    return generate_response(prompt)
