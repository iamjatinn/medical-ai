import json
import unittest
from types import SimpleNamespace
from unittest import mock

import helpers  # noqa: F401

from pydantic import ValidationError

from models.analysis_models import AbnormalFindingExplanation, ReportAnalysis
from services import ai_service, gemini_service
from services.analysis_service import render_markdown, sanitize_analysis

FINDINGS = [
    {"parameter": "Hemoglobin", "calculated_status": "Low"},
    {"parameter": "WBC", "calculated_status": "Normal"},
    {"parameter": "Glucose (Fasting)", "calculated_status": "High"},
]


def explanation(parameter, status="Low"):
    return AbnormalFindingExplanation(
        parameter=parameter, status=status, meaning="m",
        possible_causes=["c"], symptoms=["s"], lifestyle_tips=["t"],
    )


def analysis(abnormal, risk="moderate"):
    return ReportAnalysis(
        overview="Overview text", overall_risk=risk, risk_explanation="Because.",
        abnormal_findings=abnormal, normal_findings_note="WBC is fine.",
        diet_suggestions=["Spinach"], lifestyle_recommendations=["Sleep"],
        follow_up_tests=["Ferritin"], questions_for_doctor=["Why?"],
        disclaimer="AI-generated, not a diagnosis.",
    )


VALID_JSON = analysis([explanation("Hemoglobin")]).model_dump_json()


class SchemaTests(unittest.TestCase):

    def test_invalid_risk_level_is_rejected(self):
        bad = json.loads(VALID_JSON)
        bad["overall_risk"] = "catastrophic"
        with self.assertRaises(ValidationError):
            ReportAnalysis.model_validate(bad)

    def test_missing_field_is_rejected(self):
        bad = json.loads(VALID_JSON)
        del bad["disclaimer"]
        with self.assertRaises(ValidationError):
            ReportAnalysis.model_validate(bad)

    def test_invalid_status_in_an_explanation_is_rejected(self):
        with self.assertRaises(ValidationError):
            explanation("Hemoglobin", status="Normal")


class SanitizeTests(unittest.TestCase):

    def test_hallucinated_and_normal_parameters_are_dropped(self):

        raw = analysis([
            explanation("Hemoglobin"),
            explanation("Cholesterol"),          # not in the report
            explanation("WBC", "High"),          # in the report but Normal
        ])

        clean = sanitize_analysis(raw, FINDINGS)

        self.assertEqual([i.parameter for i in clean.abnormal_findings], ["Hemoglobin"])

    def test_status_is_corrected_to_the_calculated_one(self):

        raw = analysis([explanation("Glucose (Fasting)", "Low")])   # AI got it wrong

        clean = sanitize_analysis(raw, FINDINGS)

        self.assertEqual(clean.abnormal_findings[0].status, "High")


class RenderTests(unittest.TestCase):

    def test_markdown_contains_all_sections(self):

        text = render_markdown(analysis([explanation("Hemoglobin")]))

        for expected in (
            "Medical Report Summary", "Abnormal Findings", "Hemoglobin (Low)",
            "Overall risk", "Moderate",
            "Spinach", "Ferritin", "Why?", "Disclaimer",
        ):
            self.assertIn(expected, text)

    def test_markdown_handles_no_abnormal_findings(self):
        self.assertIn("No abnormal findings", render_markdown(analysis([], risk="low")))


class ExplainReportTests(unittest.TestCase):

    def test_success_returns_summary_text_and_structured_data(self):

        with mock.patch.object(ai_service, "retrieve_knowledge", return_value=[]), \
             mock.patch.object(ai_service, "generate_structured",
                               return_value=(analysis([explanation("Hemoglobin")]), None)):

            result = ai_service.explain_report(FINDINGS)

        self.assertIn("Hemoglobin (Low)", result["summary"])
        self.assertEqual(result["analysis"]["overall_risk"], "moderate")

    def test_ai_failure_returns_friendly_message_and_no_analysis(self):

        with mock.patch.object(ai_service, "retrieve_knowledge", return_value=[]), \
             mock.patch.object(ai_service, "generate_structured",
                               return_value=(None, "AI is down")):

            result = ai_service.explain_report(FINDINGS)

        self.assertEqual(result, {"summary": "AI is down", "analysis": None})


class GeminiStructuredTests(unittest.TestCase):
    """generate_structured: validation and the single retry."""

    def fake_client(self, *texts):
        client = mock.MagicMock()
        client.models.generate_content.side_effect = [SimpleNamespace(text=t) for t in texts]
        return client

    def test_valid_json_is_parsed(self):
        client = self.fake_client(VALID_JSON)
        with mock.patch.object(gemini_service, "_get_client", return_value=client):
            result, error = gemini_service.generate_structured("p", ReportAnalysis)
        self.assertIsNone(error)
        self.assertEqual(result.overall_risk, "moderate")
        self.assertEqual(client.models.generate_content.call_count, 1)

    def test_invalid_reply_is_retried_once_then_succeeds(self):
        client = self.fake_client('{"overview": "incomplete"}', VALID_JSON)
        with mock.patch.object(gemini_service, "_get_client", return_value=client):
            result, error = gemini_service.generate_structured("p", ReportAnalysis)
        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertEqual(client.models.generate_content.call_count, 2)

    def test_two_bad_replies_give_a_friendly_error_not_a_crash(self):
        client = self.fake_client("not json", '{"overview": 1}')
        with mock.patch.object(gemini_service, "_get_client", return_value=client):
            result, error = gemini_service.generate_structured("p", ReportAnalysis)
        self.assertIsNone(result)
        self.assertIn("unavailable", error)

    def test_client_uses_the_v1beta_api(self):
        """Regression test: with the default 'v1' API, Gemini answers
        'JSON mode is not enabled for api version v1'."""

        with mock.patch.object(gemini_service, "_client", None), \
             mock.patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), \
             mock.patch.object(gemini_service.genai, "Client") as client_class:

            gemini_service._get_client()

        http_options = client_class.call_args.kwargs["http_options"]
        self.assertEqual(http_options.api_version, "v1beta")

    def test_missing_api_key_gives_a_clear_message(self):
        with mock.patch.object(gemini_service, "_get_client", side_effect=RuntimeError("no key")):
            result, error = gemini_service.generate_structured("p", ReportAnalysis)
        self.assertIsNone(result)
        self.assertIn("GEMINI_API_KEY", error)


if __name__ == "__main__":
    unittest.main()


class ModelFallbackTests(unittest.TestCase):
    """Overloaded / out-of-quota / retired models fall through to the next one."""

    def error(self, kind, code=None):
        from google.genai.errors import ClientError, ServerError

        body = {"error": {"message": "test"}}
        return ServerError(code or 503, body) if kind == "server" else ClientError(code, body)

    def client(self, *outcomes):
        client = mock.MagicMock()
        client.models.generate_content.side_effect = list(outcomes)
        return client

    def run_chain(self, client):
        return gemini_service.generate_with_fallback(
            contents="p", client=client, models=["model-a", "model-b", "model-c"]
        )

    def models_tried(self, client):
        return [c.kwargs["model"] for c in client.models.generate_content.call_args_list]

    def test_first_model_is_used_when_it_works(self):
        client = self.client("ok")
        response, model = self.run_chain(client)
        self.assertEqual((response, model), ("ok", "model-a"))
        self.assertEqual(self.models_tried(client), ["model-a"])

    def test_overload_503_quota_429_and_retired_404_fall_through(self):
        client = self.client(
            self.error("server", 503), self.error("client", 429), "third works"
        )
        response, model = self.run_chain(client)
        self.assertEqual((response, model), ("third works", "model-c"))
        self.assertEqual(self.models_tried(client), ["model-a", "model-b", "model-c"])

        client = self.client(self.error("client", 404), "second works")
        self.assertEqual(self.run_chain(client)[1], "model-b")

    def test_a_timeout_falls_through(self):
        class ReadTimeout(Exception):
            pass

        client = self.client(ReadTimeout("slow"), "second works")
        self.assertEqual(self.run_chain(client)[1], "model-b")

    def test_our_own_errors_are_not_retried_on_other_models(self):
        """A 400 (bad request) or 403 (bad key) would fail on every model."""
        for code in (400, 401, 403):
            client = self.client(self.error("client", code))
            with self.assertRaises(Exception):
                self.run_chain(client)
            self.assertEqual(self.models_tried(client), ["model-a"], code)

    def test_when_every_model_fails_the_last_error_is_raised(self):
        client = self.client(*[self.error("server", 503) for _ in range(3)])
        with self.assertRaises(Exception) as context:
            self.run_chain(client)
        self.assertEqual(context.exception.code, 503)
        self.assertEqual(len(self.models_tried(client)), 3)

    def test_structured_output_uses_the_fallback_chain(self):
        """generate_structured() must survive an overloaded first model."""
        client = self.client(self.error("server", 503), SimpleNamespace(text=VALID_JSON))
        with mock.patch.object(gemini_service, "_get_client", return_value=client), \
             mock.patch.object(gemini_service, "GEMINI_MODELS", ["model-a", "model-b"]):
            result, error = gemini_service.generate_structured("p", ReportAnalysis)
        self.assertIsNone(error)
        self.assertEqual(result.overall_risk, "moderate")
        self.assertEqual(self.models_tried(client), ["model-a", "model-b"])
