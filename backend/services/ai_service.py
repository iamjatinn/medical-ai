import json

from services.gemini_service import generate_response
from services.knowledge_service import retrieve_knowledge


def explain_report(findings):

    knowledge = retrieve_knowledge(findings)

    report = {
        "findings": findings,
        "medical_knowledge": knowledge
    }

    report_json = json.dumps(report, indent=2)

    prompt = f"""
You are an experienced AI medical assistant.

Below is a structured medical report along with trusted medical knowledge.

{report_json}

Instructions:

1. Explain only the findings in the report.
2. Use the provided medical knowledge while explaining.
3. Do not invent new medical facts.
4. Explain in simple English.
5. Suggest general healthy lifestyle improvements.
6. Do not diagnose diseases.
7. Recommend consulting a qualified doctor.
8. Format your answer using headings and bullet points.
9. Keep the explanation concise.
"""

    return generate_response(prompt)