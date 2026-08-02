import json

from services.gemini_service import generate_response
from services.rag_knowledge_service import retrieve_knowledge
from prompts.report_prompt import REPORT_PROMPT


def explain_report(findings,rag):

    knowledge = retrieve_knowledge(findings,rag)

    print("\n========== RETRIEVED KNOWLEDGE ==========\n")

    for i, chunk in enumerate(knowledge, start=1):

        print(f"Chunk {i}:")

        print(chunk)

        print("-" * 60)

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