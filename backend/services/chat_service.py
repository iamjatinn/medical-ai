import json

from services.report_storage_service import (
    load_report,
    save_chat
)

from services.rag_knowledge_service import retrieve_knowledge
from services.gemini_service import generate_response


SYSTEM_PROMPT = """
You are Medical AI Assistant.

You ONLY answer questions related to:

• Medical reports
• Blood tests
• Laboratory parameters
• Diseases
• Nutrition
• Medicines (general information only)
• Healthy lifestyle
• Medical terminology

If the user asks anything unrelated to health or the uploaded report,
politely refuse.

Example:

"I'm designed to answer questions about your uploaded medical report and general health information only."

Never diagnose.

Never prescribe medicines.

Always recommend consulting a doctor for diagnosis.

Use previous conversation whenever needed.
"""


def ask_question(report_id: str, question: str):

    report = load_report(report_id)

    findings = report["findings"]

    knowledge = retrieve_knowledge(findings)

    history = report.get("chat_history", [])

    history = history[-10:]

    history_text = ""

    for msg in history:

        history_text += (
            f"{msg['role'].upper()}: "
            f"{msg['content']}\n"
        )

    prompt = f"""
{SYSTEM_PROMPT}

==========================
PATIENT REPORT
==========================

{json.dumps(findings, indent=2)}

==========================
MEDICAL KNOWLEDGE
==========================

{chr(10).join(knowledge)}

==========================
PREVIOUS CHAT
==========================

{history_text}

==========================
CURRENT QUESTION
==========================

{question}

Answer naturally.
"""

    answer = generate_response(prompt)

    save_chat(
        report_id,
        question,
        answer
    )

    return answer