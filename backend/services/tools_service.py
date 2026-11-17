"""Tools the chat assistant can call (LLM function calling).

Why tools? The model should not guess facts about *this* report or do
arithmetic in its head. It asks a tool, gets an exact answer, and explains it.

Security: every tool is bound to ONE report (`report`) when ReportTools is
created. The model never chooses a report id, so it cannot read other
people's reports no matter what the user types.
"""

import logging

from google.genai import types

from config import TOP_K
from services.rag_knowledge_service import get_rag

logger = logging.getLogger(__name__)

MAX_QUERY_CHARS = 300


def _range_text(reference_range) -> str:

    low, high = reference_range["min"], reference_range["max"]

    if low is not None and high is not None:
        return f"{low:g} - {high:g}"
    if high is not None:
        return f"< {high:g}"
    if low is not None:
        return f"> {low:g}"
    return "not available"


def _summary(finding) -> dict:

    return {
        "parameter": finding["parameter"],
        "value": finding["value"],
        "unit": finding["unit"],
        "reference_range": _range_text(finding["reference_range"]),
        "status": finding["calculated_status"],
    }


class ReportTools:
    """The four tools, bound to a single report."""

    def __init__(self, report: dict):

        self.findings = report["findings"]

    # ---------------- the tools ---------------- #

    def search_knowledge(self, query: str) -> dict:
        """Search the medical knowledge base (RAG) for general information."""

        results = get_rag().search(str(query)[:MAX_QUERY_CHARS], k=TOP_K)

        return {"passages": [result["text"] for result in results]}

    def get_report_findings(self, status: str = None) -> dict:
        """List the lab results in this report, optionally filtered by status."""

        wanted = str(status).strip().lower() if status else None

        items = [
            _summary(finding)
            for finding in self.findings
            if wanted is None or finding["calculated_status"].lower() == wanted
        ]

        return {"count": len(items), "findings": items}

    def _find(self, parameter: str):

        name = str(parameter).strip().lower()

        for finding in self.findings:
            if finding["parameter"].lower() == name:
                return finding

        for finding in self.findings:                       # partial match, e.g. "glucose"
            if name and name in finding["parameter"].lower():
                return finding

        return None

    def get_parameter_details(self, parameter: str) -> dict:
        """Exact value, unit, reference range and status of one test."""

        finding = self._find(parameter)

        if finding is None:
            return {
                "error": f"'{parameter}' is not in this report",
                "available_parameters": [f["parameter"] for f in self.findings],
            }

        return _summary(finding)

    def compute_deviation(self, parameter: str) -> dict:
        """How far (in percent) a result is outside its reference range."""

        finding = self._find(parameter)

        if finding is None:
            return {"error": f"'{parameter}' is not in this report"}

        value = finding["value"]
        low, high = finding["reference_range"]["min"], finding["reference_range"]["max"]

        result = {"parameter": finding["parameter"], "value": value,
                  "reference_range": _range_text(finding["reference_range"])}

        if low is not None and value < low:
            result["position"] = "below the range"
            result["percent_below_minimum"] = round((low - value) / low * 100, 1)

        elif high is not None and value > high:
            result["position"] = "above the range"
            result["percent_above_maximum"] = round((value - high) / high * 100, 1)

        else:
            result["position"] = "within the range"

        return result

    # ---------------- dispatch ---------------- #

    def execute(self, name: str, args: dict) -> dict:
        """Run a tool requested by the model. Never raises: errors are returned
        to the model so it can recover or explain."""

        tools = {
            "search_knowledge": self.search_knowledge,
            "get_report_findings": self.get_report_findings,
            "get_parameter_details": self.get_parameter_details,
            "compute_deviation": self.compute_deviation,
        }

        function = tools.get(name)

        if function is None:
            return {"error": f"unknown tool '{name}'"}

        try:
            return function(**(args or {}))
        except TypeError:
            return {"error": f"bad arguments for tool '{name}'"}
        except Exception:
            logger.exception("Tool %s failed", name)
            return {"error": f"tool '{name}' failed"}


def _string(description: str):
    return types.Schema(type=types.Type.STRING, description=description)


TOOL_DECLARATIONS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="search_knowledge",
        description=(
            "Search the medical knowledge base for general information about "
            "a condition, symptom, cause, diet or lifestyle topic. Use it for "
            "general medical questions, not for the user's own numbers."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"query": _string("What to look up, e.g. 'iron rich foods'")},
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_report_findings",
        description=(
            "List the lab results in the user's report with value, unit, "
            "reference range and status (Low, Normal or High). Use it for "
            "questions like 'which results are abnormal?'."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"status": types.Schema(
                type=types.Type.STRING,
                enum=["Low", "Normal", "High"],
                description="Optional: only return results with this status",
            )},
        ),
    ),
    types.FunctionDeclaration(
        name="get_parameter_details",
        description=(
            "Get the exact value, unit, reference range and status of ONE "
            "test from the user's report, e.g. Hemoglobin or Vitamin D."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"parameter": _string("Test name, e.g. 'Hemoglobin'")},
            required=["parameter"],
        ),
    ),
    types.FunctionDeclaration(
        name="compute_deviation",
        description=(
            "Calculate exactly how far (in percent) one test result is below "
            "or above its reference range. Use it instead of doing the "
            "arithmetic yourself."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"parameter": _string("Test name, e.g. 'Vitamin D'")},
            required=["parameter"],
        ),
    ),
])
