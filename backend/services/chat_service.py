import json
import logging

from services import agent_service
from services.gemini_service import generate_response
from services.rag_knowledge_service import retrieve_for_question, retrieve_knowledge
from services.report_storage_service import load_report, save_chat
from services.tools_service import ReportTools

logger = logging.getLogger(__name__)

HISTORY_MESSAGES = 10


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


AGENT_INSTRUCTIONS = SYSTEM_PROMPT + """

You have tools. Use them instead of guessing:
- For facts about THIS user's report (values, ranges, status) call
  get_report_findings or get_parameter_details. Never invent numbers.
- For "how far from normal" or any percentage call compute_deviation.
  Never do the arithmetic yourself.
- For general medical information (causes, symptoms, foods, lifestyle) call
  search_knowledge and base your answer on what it returns.
- If the question is not about health or the report, refuse politely and do
  not call any tool.
Answer in clear, simple language and keep it concise.
"""


def _fallback_answer(report, question, history):
    """The original approach: put the knowledge straight into one prompt.
    Used when the agent cannot run (for example an API problem)."""

    findings = report["findings"]

    knowledge = list(dict.fromkeys(
        retrieve_knowledge(findings) + retrieve_for_question(question)
    )) or ["No additional medical knowledge was retrieved."]

    history_text = "".join(
        f"{message['role'].upper()}: {message['content']}\n" for message in history
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

    return generate_response(prompt)


def ask_question(report_id: str, question: str, *, user_id: int):
    """Answer a question about one of the user's own reports.

    Returns {"answer": str, "tools_used": [names]}.
    Raises ReportNotFoundError if the report is not found or not owned by user_id.
    """

    report = load_report(report_id, user_id=user_id)

    history = report.get("chat_history", [])[-HISTORY_MESSAGES:]

    try:
        result = agent_service.run_agent(
            tools=ReportTools(report),
            question=question,
            history=history,
            system_instruction=AGENT_INSTRUCTIONS,
        )

        answer, tools_used = result["answer"], result["tools_used"]

        if not answer:
            raise ValueError("the agent returned an empty answer")

    except Exception:
        logger.exception("Agent failed; using the plain RAG prompt instead")

        answer, tools_used = _fallback_answer(report, question, history), []

    save_chat(report_id, question, answer, user_id=user_id)

    return {"answer": answer, "tools_used": tools_used}
