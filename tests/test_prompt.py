import json
import unittest
from unittest import mock

import helpers  # noqa: F401

from prompts.report_prompt import REPORT_PROMPT
from services import ai_service


class PromptTests(unittest.TestCase):

    def test_template_has_a_report_placeholder(self):
        """Regression test: the {report} placeholder was once deleted, so the
        AI never saw the patient's findings or the retrieved knowledge."""

        self.assertIn("{report}", REPORT_PROMPT)

        self.assertIn("MARKER-123", REPORT_PROMPT.format(report="MARKER-123"))

    def test_explain_report_sends_findings_and_knowledge_to_the_ai(self):

        findings = [{"parameter": "Hemoglobin", "calculated_status": "Low"}]

        with mock.patch.object(
            ai_service, "retrieve_knowledge", return_value=["Iron helps make hemoglobin."]
        ), mock.patch.object(
            ai_service, "generate_response", return_value="ok"
        ) as generate:

            ai_service.explain_report(findings)

        prompt = generate.call_args.args[0]

        self.assertIn(json.dumps("Hemoglobin"), prompt)
        self.assertIn("Iron helps make hemoglobin.", prompt)


if __name__ == "__main__":
    unittest.main()
