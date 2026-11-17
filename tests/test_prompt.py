import json
import unittest
from unittest import mock

import helpers  # noqa: F401

from models.analysis_models import ReportAnalysis, ReportAnalysisDraft
from prompts.report_prompt import REPORT_PROMPT, STRUCTURED_REPORT_PROMPT
from services import ai_service

ANALYSIS = ReportAnalysis(
    overview="o", overall_risk="mild", risk_explanation="r",
    abnormal_findings=[], normal_findings_note="n", diet_suggestions=[],
    lifestyle_recommendations=[], follow_up_tests=[], questions_for_doctor=[],
    disclaimer="d",
)


class PromptTests(unittest.TestCase):

    def test_templates_have_a_report_placeholder(self):
        """Regression test: the {report} placeholder was once deleted, so the
        AI never saw the patient's findings or the retrieved knowledge."""

        for template in (REPORT_PROMPT, STRUCTURED_REPORT_PROMPT):
            self.assertIn("{report}", template)
            self.assertIn("MARKER-123", template.format(report="MARKER-123"))

    def test_explain_report_sends_findings_and_knowledge_to_the_ai(self):

        findings = [{"parameter": "Hemoglobin", "calculated_status": "Low"}]

        with mock.patch.object(
            ai_service, "retrieve_with_sources", return_value=(["Iron helps make hemoglobin."], [])
        ), mock.patch.object(
            ai_service, "generate_structured", return_value=(ANALYSIS, None)
        ) as generate:

            ai_service.explain_report(findings)

        prompt, schema = generate.call_args.args

        self.assertIn(json.dumps("Hemoglobin"), prompt)
        self.assertIn("Iron helps make hemoglobin.", prompt)
        self.assertIs(schema, ReportAnalysisDraft)


if __name__ == "__main__":
    unittest.main()
