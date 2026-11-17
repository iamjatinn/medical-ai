import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers

from fastapi.testclient import TestClient

import main
from routers import upload as upload_router
from services import report_storage_service


class ApiTests(unittest.TestCase):

    def setUp(self):

        helpers.patch_database(self)
        helpers.fresh_limiters(self)

        self.client = TestClient(main.app)
        self.headers, self.user_id = helpers.register(self.client)

        # Keep uploaded files away from the real folder.
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.uploads = Path(folder.name)

        for patcher in (
            mock.patch.object(upload_router, "UPLOAD_DIR", self.uploads),
            # no Gemini / FAISS needed for these tests
            mock.patch(
                "services.medical_report_service.explain_report",
                return_value={"summary": "test summary", "analysis": None},
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def upload(self, content, name="report.pdf", content_type="application/pdf", headers=None):
        return self.client.post(
            "/upload-report",
            files={"file": (name, content, content_type)},
            headers=self.headers if headers is None else headers,
        )

    def test_health(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_valid_report_is_analysed_saved_for_the_user_and_upload_is_deleted(self):

        response = self.upload(helpers.SAMPLE_PDF.read_bytes(), name="my report.pdf")

        self.assertEqual(response.status_code, 200)

        result = response.json()["result"]

        self.assertEqual(result["filename"], "my report.pdf")
        self.assertEqual(len(result["findings"]), 6)
        self.assertEqual(result["ai_summary"], "test summary")
        self.assertEqual(list(self.uploads.iterdir()), [])          # temp copy removed

        saved = report_storage_service.load_report(result["report_id"], user_id=self.user_id)
        self.assertEqual(saved["findings"][0]["parameter"], "Hemoglobin")

    def test_path_in_filename_is_stripped(self):

        response = self.upload(helpers.SAMPLE_PDF.read_bytes(), name="..\\..\\evil\\report.pdf")

        self.assertEqual(response.json()["result"]["filename"], "report.pdf")

    def test_non_pdf_is_rejected(self):
        self.assertEqual(self.upload(b"hello", "a.txt", "text/plain").status_code, 400)

    def test_fake_pdf_is_rejected_by_magic_bytes(self):
        self.assertEqual(self.upload(b"not really a pdf").status_code, 400)

    def test_empty_file_is_rejected(self):
        self.assertEqual(self.upload(b"").status_code, 400)

    def test_oversized_file_is_rejected(self):

        with mock.patch.object(upload_router, "MAX_UPLOAD_BYTES", 100):
            response = self.upload(b"%PDF-" + b"0" * 500)

        self.assertEqual(response.status_code, 413)

    def test_pdf_without_lab_results_gives_a_clear_422(self):

        import pymupdf

        document = pymupdf.open()
        document.new_page().insert_text((72, 72), "Dear patient, see you soon.")

        response = self.upload(document.tobytes())

        self.assertEqual(response.status_code, 422)
        self.assertIn("No laboratory results", response.json()["detail"])

    def test_chat_unknown_or_malicious_report_id_is_404(self):

        for report_id in ("11111111-1111-4111-8111-111111111111", "../../etc/passwd"):
            response = self.client.post(
                "/chat", json={"report_id": report_id, "question": "hi"}, headers=self.headers
            )
            self.assertEqual(response.status_code, 404, report_id)

    def test_chat_rejects_empty_question(self):

        response = self.client.post(
            "/chat",
            json={"report_id": "11111111-1111-4111-8111-111111111111", "question": ""},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 422)

    def test_chat_uses_report_and_saves_history(self):

        report = report_storage_service.save_report("r.pdf", [], "summary", user_id=self.user_id)

        with mock.patch(
            "services.agent_service.run_agent",
            return_value={"answer": "answer", "tools_used": ["search_knowledge"], "steps": 2},
        ):
            response = self.client.post(
                "/chat",
                json={"report_id": report["report_id"], "question": "What is this?"},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "answer")
        self.assertEqual(response.json()["tools_used"], ["search_knowledge"])

        saved = report_storage_service.load_report(report["report_id"], user_id=self.user_id)

        self.assertEqual([m["role"] for m in saved["chat_history"]], ["user", "assistant"])


if __name__ == "__main__":
    unittest.main()
