import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import helpers  # noqa: F401

from google.genai import types
from sqlalchemy.orm import sessionmaker

import database
from models import db_models  # noqa: F401
from services import agent_service, chat_service
from services import report_storage_service as storage
from services import tools_service
from services.tools_service import ReportTools

FINDINGS = [
    {"parameter": "Hemoglobin", "value": 11.2, "unit": "g/dL",
     "reference_range": {"min": 13.5, "max": 17.5}, "calculated_status": "Low"},
    {"parameter": "WBC", "value": 9800.0, "unit": "/uL",
     "reference_range": {"min": 4000.0, "max": 11000.0}, "calculated_status": "Normal"},
    {"parameter": "Glucose (Fasting)", "value": 145.0, "unit": "mg/dL",
     "reference_range": {"min": 70.0, "max": 99.0}, "calculated_status": "High"},
    {"parameter": "Vitamin D", "value": 18.0, "unit": "ng/mL",
     "reference_range": {"min": 30.0, "max": 100.0}, "calculated_status": "Low"},
    {"parameter": "LDL", "value": 90.0, "unit": "mg/dL",
     "reference_range": {"min": None, "max": 100.0}, "calculated_status": "Normal"},
]

REPORT = {"report_id": "r1", "findings": FINDINGS, "chat_history": []}


class ToolTests(unittest.TestCase):

    def setUp(self):
        self.tools = ReportTools(REPORT)

    def test_get_parameter_details_is_case_insensitive_and_allows_partial_names(self):
        self.assertEqual(self.tools.get_parameter_details("hemoglobin")["value"], 11.2)
        self.assertEqual(self.tools.get_parameter_details("glucose")["parameter"], "Glucose (Fasting)")
        self.assertEqual(self.tools.get_parameter_details("Vitamin D")["reference_range"], "30 - 100")

    def test_unknown_parameter_returns_an_error_with_the_valid_names(self):
        result = self.tools.get_parameter_details("Cholesterol")
        self.assertIn("not in this report", result["error"])
        self.assertIn("Hemoglobin", result["available_parameters"])

    def test_one_sided_range_is_described_correctly(self):
        self.assertEqual(self.tools.get_parameter_details("LDL")["reference_range"], "< 100")

    def test_get_report_findings_can_filter_by_status(self):
        self.assertEqual(self.tools.get_report_findings()["count"], 5)
        abnormal = self.tools.get_report_findings("low")
        self.assertEqual([f["parameter"] for f in abnormal["findings"]], ["Hemoglobin", "Vitamin D"])
        self.assertEqual(self.tools.get_report_findings("High")["count"], 1)

    def test_compute_deviation_does_the_arithmetic_exactly(self):
        # (30 - 18) / 30 = 40 %
        self.assertEqual(self.tools.compute_deviation("Vitamin D")["percent_below_minimum"], 40.0)
        # (145 - 99) / 99 = 46.5 %
        self.assertEqual(self.tools.compute_deviation("Glucose")["percent_above_maximum"], 46.5)
        self.assertEqual(self.tools.compute_deviation("WBC")["position"], "within the range")

    def test_search_knowledge_returns_passages_from_the_index(self):
        fake_rag = mock.Mock()
        fake_rag.search.return_value = [{"text": "Iron-rich foods include spinach.", "score": 0.7}]

        with mock.patch.object(tools_service, "get_rag", return_value=fake_rag):
            result = self.tools.search_knowledge("iron foods")

        self.assertEqual(result, {"passages": ["Iron-rich foods include spinach."]})

    def test_execute_never_raises(self):
        self.assertIn("unknown tool", self.tools.execute("delete_everything", {})["error"])
        self.assertIn("bad arguments", self.tools.execute("get_parameter_details", {"wrong": 1})["error"])

    def test_tools_only_see_their_own_report(self):
        """A tool is bound to one report; there is no argument to pick another."""
        other = ReportTools({"findings": []})
        self.assertEqual(other.get_report_findings()["count"], 0)
        self.assertIn("error", other.get_parameter_details("Hemoglobin"))


def text_response(text):
    return SimpleNamespace(function_calls=None, text=text, candidates=[])


def tool_response(name, args):
    content = types.Content(role="model", parts=[types.Part.from_function_call(name=name, args=args)])
    return SimpleNamespace(
        function_calls=[SimpleNamespace(name=name, args=args)],
        text=None,
        candidates=[SimpleNamespace(content=content)],
    )


def fake_client(*responses):
    client = mock.MagicMock()
    client.models.generate_content.side_effect = list(responses)
    return client


class AgentLoopTests(unittest.TestCase):

    def run_agent(self, client, **kwargs):
        return agent_service.run_agent(
            tools=ReportTools(REPORT), question="q", history=[],
            system_instruction="system", client=client, **kwargs,
        )

    def test_answers_directly_when_no_tool_is_needed(self):
        result = self.run_agent(fake_client(text_response("Hello")))
        self.assertEqual(result, {"answer": "Hello", "tools_used": [], "steps": 1})

    def test_calls_a_tool_then_answers_from_its_result(self):
        client = fake_client(
            tool_response("compute_deviation", {"parameter": "Vitamin D"}),
            text_response("Your vitamin D is 40% below the minimum."),
        )

        result = self.run_agent(client)

        self.assertEqual(result["tools_used"], ["compute_deviation"])
        self.assertEqual(result["steps"], 2)
        self.assertIn("40%", result["answer"])

        # the tool's real result was sent back to the model
        second_call_contents = client.models.generate_content.call_args_list[1].kwargs["contents"]
        function_response = second_call_contents[-1].parts[0].function_response
        self.assertEqual(function_response.name, "compute_deviation")
        self.assertEqual(function_response.response["result"]["percent_below_minimum"], 40.0)

    def test_several_tool_rounds_are_recorded_in_order(self):
        client = fake_client(
            tool_response("get_report_findings", {"status": "Low"}),
            tool_response("search_knowledge", {"query": "low iron"}),
            text_response("done"),
        )

        with mock.patch.object(tools_service, "get_rag") as get_rag:
            get_rag.return_value.search.return_value = []
            result = self.run_agent(client)

        self.assertEqual(result["tools_used"], ["get_report_findings", "search_knowledge"])

    def test_a_looping_model_is_stopped_at_the_step_limit(self):
        looping = [tool_response("get_report_findings", {}) for _ in range(3)]
        client = fake_client(*looping, text_response("final answer without tools"))

        result = self.run_agent(client, max_steps=3)

        self.assertEqual(result["answer"], "final answer without tools")
        self.assertEqual(len(result["tools_used"]), 3)
        self.assertEqual(client.models.generate_content.call_count, 4)   # 3 rounds + 1 tool-less
        self.assertIsNone(client.models.generate_content.call_args.kwargs["config"].tools)

    def test_a_tool_error_is_given_to_the_model_not_raised(self):
        client = fake_client(
            tool_response("get_parameter_details", {"parameter": "Cholesterol"}),
            text_response("That test is not in your report."),
        )

        result = self.run_agent(client)

        self.assertIn("not in your report", result["answer"])

    def test_stored_history_is_sent_with_the_right_roles(self):
        client = fake_client(text_response("ok"))

        agent_service.run_agent(
            tools=ReportTools(REPORT), question="new question",
            history=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}],
            system_instruction="system", client=client,
        )

        contents = client.models.generate_content.call_args.kwargs["contents"]

        self.assertEqual([c.role for c in contents], ["user", "model", "user"])
        self.assertEqual(contents[-1].parts[0].text, "new question")


class ChatServiceTests(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)

        engine = database.make_engine(f"sqlite:///{Path(folder.name, 't.db').as_posix()}")
        database.Base.metadata.create_all(engine)
        self.addCleanup(engine.dispose)

        patcher = mock.patch.object(database, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
        patcher.start()
        self.addCleanup(patcher.stop)

        self.report = storage.save_report("lab.pdf", FINDINGS, "summary")

    def test_agent_answer_and_tools_are_returned_and_saved(self):

        with mock.patch.object(
            agent_service, "run_agent",
            return_value={"answer": "agent answer", "tools_used": ["compute_deviation"], "steps": 2},
        ):
            result = chat_service.ask_question(self.report["report_id"], "How low is my vitamin D?")

        self.assertEqual(result, {"answer": "agent answer", "tools_used": ["compute_deviation"]})

        history = storage.load_report(self.report["report_id"])["chat_history"]
        self.assertEqual([m["content"] for m in history], ["How low is my vitamin D?", "agent answer"])

    def test_if_the_agent_fails_the_plain_rag_prompt_is_used(self):

        with mock.patch.object(agent_service, "run_agent", side_effect=RuntimeError("api down")), \
             mock.patch.object(chat_service, "retrieve_knowledge", return_value=[]), \
             mock.patch.object(chat_service, "retrieve_for_question", return_value=[]), \
             mock.patch.object(chat_service, "generate_response", return_value="fallback answer"):

            result = chat_service.ask_question(self.report["report_id"], "hi")

        self.assertEqual(result, {"answer": "fallback answer", "tools_used": []})

    def test_an_empty_agent_answer_also_falls_back(self):

        with mock.patch.object(
            agent_service, "run_agent", return_value={"answer": "", "tools_used": [], "steps": 1}
        ), mock.patch.object(chat_service, "retrieve_knowledge", return_value=[]), \
             mock.patch.object(chat_service, "retrieve_for_question", return_value=[]), \
             mock.patch.object(chat_service, "generate_response", return_value="fallback"):

            result = chat_service.ask_question(self.report["report_id"], "hi")

        self.assertEqual(result["answer"], "fallback")


if __name__ == "__main__":
    unittest.main()
