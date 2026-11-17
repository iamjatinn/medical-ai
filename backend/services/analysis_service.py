"""Post-processing of the structured AI answer.

Validation by the schema guarantees the *shape* of the JSON. These helpers
check the *content* against the real findings and render the text version.
"""

import logging

from models.analysis_models import ReportAnalysis

logger = logging.getLogger(__name__)

RISK_LABELS = {
    "low": "🟢 Low",
    "mild": "🟡 Mild",
    "moderate": "🟠 Moderate",
    "high": "🔴 High",
}


def sanitize_analysis(analysis: ReportAnalysis, findings) -> ReportAnalysis:
    """Make the AI's answer consistent with the rule-based findings.

    - Drop explanations for parameters that are not in the report
      (a hallucinated test).
    - Drop explanations for tests that were not actually abnormal.
    - Make sure the status in each explanation matches the calculated one.
    """

    status_by_parameter = {
        finding["parameter"].strip().lower(): finding["calculated_status"]
        for finding in findings
    }

    kept = []

    for item in analysis.abnormal_findings:

        real_status = status_by_parameter.get(item.parameter.strip().lower())

        if real_status not in ("Low", "High"):
            logger.warning(
                "Dropping AI explanation for '%s' (not an abnormal finding in the report)",
                item.parameter,
            )
            continue

        kept.append(item.model_copy(update={"status": real_status}))

    return analysis.model_copy(update={"abnormal_findings": kept})


def _bullets(items) -> str:

    return "\n".join(f"- {item}" for item in items) if items else "- None"


def render_markdown(analysis: ReportAnalysis) -> str:
    """Readable text version, shown by the existing UI and stored as ai_summary."""

    parts = [
        "# 🩺 Medical Report Summary",
        analysis.overview,
        "---",
        "# 🔍 Abnormal Findings",
    ]

    if analysis.abnormal_findings:

        for item in analysis.abnormal_findings:
            parts += [
                f"## {item.parameter} ({item.status})",
                item.meaning,
                f"**Possible causes**\n{_bullets(item.possible_causes)}",
                f"**Symptoms that may be linked**\n{_bullets(item.symptoms)}",
                f"**Lifestyle tips**\n{_bullets(item.lifestyle_tips)}",
            ]
    else:
        parts.append("No abnormal findings were detected.")

    parts += [
        "---",
        "# ✅ Normal Findings",
        analysis.normal_findings_note,
        "---",
        "# ⚠ Risk Assessment",
        f"**Overall risk: {RISK_LABELS[analysis.overall_risk]}**",
        analysis.risk_explanation,
        "---",
        "# 🥗 Diet Suggestions",
        _bullets(analysis.diet_suggestions),
        "# 🏃 Lifestyle Recommendations",
        _bullets(analysis.lifestyle_recommendations),
        "# 🧪 Possible Follow-up Tests",
        _bullets(analysis.follow_up_tests),
        "# 👨‍⚕ Questions to Ask Your Doctor",
        _bullets(analysis.questions_for_doctor),
        "---",
        "# 📌 Disclaimer",
        analysis.disclaimer,
    ]

    sources = getattr(analysis, "sources", [])

    if sources:
        source_lines = [
            f"- {s.title}" + (f" ({s.url})" if s.url else "") for s in sources
        ]

        parts += ["---", "# 📚 Sources", chr(10).join(source_lines)]

        credits = sorted({s.credit for s in sources if s.credit})

        if credits:
            parts.append("Information adapted from: " + "; ".join(credits) + ".")

    return "\n\n".join(parts)
