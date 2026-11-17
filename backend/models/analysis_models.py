"""The shape of the AI's answer.

Gemini is told to return JSON in exactly this shape (structured output), and
the reply is then validated with Pydantic before anything is stored or shown.
No free-form text parsing is needed anywhere.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel


class AbnormalFindingExplanation(BaseModel):
    parameter: str                     # must match a parameter from the report
    status: Literal["Low", "High"]
    meaning: str
    possible_causes: List[str]
    symptoms: List[str]
    lifestyle_tips: List[str]


class ReportAnalysis(BaseModel):
    overview: str
    overall_risk: Literal["low", "mild", "moderate", "high"]
    risk_explanation: str
    abnormal_findings: List[AbnormalFindingExplanation]
    normal_findings_note: str
    diet_suggestions: List[str]
    lifestyle_recommendations: List[str]
    follow_up_tests: List[str]
    questions_for_doctor: List[str]
    disclaimer: str


class AnalysisResult(BaseModel):
    """What the API sends back: the structured analysis plus its text form."""

    analysis: Optional[ReportAnalysis] = None
    summary: str
