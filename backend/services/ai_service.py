import json
import logging

from models.analysis_models import ReportAnalysis
from prompts.report_prompt import STRUCTURED_REPORT_PROMPT
from services.analysis_service import render_markdown, sanitize_analysis
from services.gemini_service import generate_structured
from services.rag_knowledge_service import retrieve_knowledge

logger = logging.getLogger(__name__)


def explain_report(findings):
    """Explain the findings with an LLM, using retrieved medical knowledge.

    Returns {"summary": <text>, "analysis": <dict or None>}:
      - analysis: the validated structured answer (None if the AI failed)
      - summary:  readable text made from it (or a friendly error message)
    """

    knowledge = retrieve_knowledge(findings)

    for number, chunk in enumerate(knowledge, start=1):
        logger.debug("Retrieved knowledge chunk %d: %s", number, chunk)

    prompt = STRUCTURED_REPORT_PROMPT.format(
        report=json.dumps(
            {"findings": findings, "medical_knowledge": knowledge},
            indent=2,
        )
    )

    analysis, error_message = generate_structured(prompt, ReportAnalysis)

    if analysis is None:
        return {"summary": error_message, "analysis": None}

    analysis = sanitize_analysis(analysis, findings)

    return {
        "summary": render_markdown(analysis),
        "analysis": analysis.model_dump(),
    }
