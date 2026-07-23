import json

from services.gemini_service import generate_response
from services.knowledge_service import retrieve_knowledge
from prompts.report_prompt import REPORT_PROMPT


def explain_report(findings):

    knowledge = retrieve_knowledge(findings)

    report_data = {
        "findings": findings,
        "medical_knowledge": knowledge
    }

    structured_report = json.dumps(
        report_data,
        indent=2
    )

    prompt = REPORT_PROMPT.format(
        report=structured_report
    )

    return generate_response(prompt)