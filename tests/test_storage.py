import unittest

import helpers

from sqlalchemy import inspect

import database
from models import db_models
from models.db_models import ChatMessage, Finding
from services import auth_service
from services import report_storage_service as storage

FINDINGS = [
    {
        "parameter": "Hemoglobin", "value": 11.2, "unit": "g/dL",
        "reference_range": {"min": 13.5, "max": 17.5},
        "reported_status": "Low", "calculated_status": "Low", "status_match": True,
    },
    {
        "parameter": "LDL", "value": 90.0, "unit": "mg/dL",
        "reference_range": {"min": None, "max": 100.0},      # one-sided range
        "reported_status": None, "calculated_status": "Normal", "status_match": None,
    },
]


class StorageTests(unittest.TestCase):

    def setUp(self):
        self.engine = helpers.patch_database(self)
        self.alice = auth_service.create_user("alice@example.com", "password-one").id
        self.bob = auth_service.create_user("bob@example.com", "password-two").id

    def save(self, **kwargs):
        defaults = dict(filename="lab.pdf", findings=FINDINGS, ai_summary="summary", user_id=self.alice)
        defaults.update(kwargs)
        return storage.save_report(
            defaults["filename"], defaults["findings"], defaults["ai_summary"],
            defaults.get("analysis"), user_id=defaults["user_id"],
        )

    def test_tables_exist(self):
        self.assertEqual(
            set(inspect(self.engine).get_table_names()),
            {"users", "reports", "findings", "chat_messages"},
        )

    def test_save_then_load_round_trip_keeps_order_and_ranges(self):

        saved = self.save(ai_summary="summary text")
        loaded = storage.load_report(saved["report_id"], user_id=self.alice)

        self.assertEqual(loaded["filename"], "lab.pdf")
        self.assertEqual(loaded["ai_summary"], "summary text")
        self.assertEqual([f["parameter"] for f in loaded["findings"]], ["Hemoglobin", "LDL"])
        self.assertEqual(loaded["findings"][1]["reference_range"], {"min": None, "max": 100.0})
        self.assertIsNone(loaded["findings"][1]["status_match"])
        self.assertEqual(loaded["chat_history"], [])

    def test_structured_analysis_is_stored_as_json(self):

        analysis = {"overall_risk": "mild", "abnormal_findings": [{"parameter": "Hemoglobin"}]}

        saved = self.save(analysis=analysis)
        self.assertEqual(storage.load_report(saved["report_id"], user_id=self.alice)["analysis"], analysis)

        plain = self.save(filename="lab2.pdf", ai_summary="AI is down")      # AI failed: no analysis
        self.assertIsNone(storage.load_report(plain["report_id"], user_id=self.alice)["analysis"])

    def test_chat_history_is_saved_in_order(self):

        report = self.save()

        storage.save_chat(report["report_id"], "first question", "first answer", user_id=self.alice)
        storage.save_chat(report["report_id"], "second question", "second answer", user_id=self.alice)

        history = storage.load_report(report["report_id"], user_id=self.alice)["chat_history"]

        self.assertEqual(
            [(m["role"], m["content"]) for m in history],
            [
                ("user", "first question"), ("assistant", "first answer"),
                ("user", "second question"), ("assistant", "second answer"),
            ],
        )

    def test_unknown_and_malicious_ids_raise_not_found(self):

        for bad_id in ("11111111-1111-4111-8111-111111111111", "../../etc/passwd", "", "nope"):
            with self.assertRaises(storage.ReportNotFoundError, msg=bad_id):
                storage.load_report(bad_id, user_id=self.alice)

        with self.assertRaises(storage.ReportNotFoundError):
            storage.save_chat("11111111-1111-4111-8111-111111111111", "q", "a", user_id=self.alice)

    # ---------------- ownership: the heart of the access control ---------------- #

    def test_another_user_cannot_load_chat_or_delete_my_report(self):

        report = self.save(user_id=self.alice)
        report_id = report["report_id"]

        with self.assertRaises(storage.ReportNotFoundError):
            storage.load_report(report_id, user_id=self.bob)

        with self.assertRaises(storage.ReportNotFoundError):
            storage.save_chat(report_id, "snooping", "x", user_id=self.bob)

        with self.assertRaises(storage.ReportNotFoundError):
            storage.delete_report(report_id, user_id=self.bob)

        # and nothing changed for the real owner
        owner_view = storage.load_report(report_id, user_id=self.alice)
        self.assertEqual(owner_view["chat_history"], [])

    def test_list_reports_only_returns_my_own(self):

        mine = self.save(filename="mine.pdf", user_id=self.alice)
        self.save(filename="bobs.pdf", user_id=self.bob)

        listed = storage.list_reports(user_id=self.alice)

        self.assertEqual([r["report_id"] for r in listed], [mine["report_id"]])
        self.assertEqual(listed[0]["abnormal_count"], 1)

    def test_reports_without_an_owner_are_visible_to_nobody(self):
        """Reports saved before accounts existed have user_id = NULL."""

        legacy = self.save()

        with database.SessionLocal() as session:
            session.get(db_models.Report, legacy["report_id"]).user_id = None
            session.commit()

        for user in (self.alice, self.bob):
            with self.assertRaises(storage.ReportNotFoundError):
                storage.load_report(legacy["report_id"], user_id=user)
            self.assertEqual(storage.list_reports(user_id=user), [])

    def test_deleting_a_report_removes_its_findings_and_messages(self):

        report = self.save()
        storage.save_chat(report["report_id"], "q", "a", user_id=self.alice)

        storage.delete_report(report["report_id"], user_id=self.alice)

        with database.SessionLocal() as session:
            self.assertEqual(session.query(Finding).count(), 0)
            self.assertEqual(session.query(ChatMessage).count(), 0)

    def test_old_table_without_new_columns_is_migrated(self):
        """A database created before structured outputs / accounts has no
        'analysis' or 'user_id' column; init_db() must add them without
        losing data."""

        import tempfile
        from pathlib import Path

        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)

        old_engine = database.make_engine(f"sqlite:///{Path(folder.name, 'old.db').as_posix()}")
        self.addCleanup(old_engine.dispose)

        with old_engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE reports (id VARCHAR(36) PRIMARY KEY, filename VARCHAR(255), "
                "ai_summary TEXT, created_at DATETIME)"
            )
            connection.exec_driver_sql(
                "INSERT INTO reports VALUES ('11111111-1111-4111-8111-111111111111', "
                "'old.pdf', 'old summary', '2026-01-01 00:00:00')"
            )

        database.init_db(old_engine)
        database.init_db(old_engine)          # running it twice must be harmless

        columns = {c["name"] for c in inspect(old_engine).get_columns("reports")}
        self.assertTrue({"analysis", "user_id"} <= columns)

        with old_engine.connect() as connection:
            row = connection.exec_driver_sql("SELECT filename, analysis, user_id FROM reports").fetchone()

        self.assertEqual(tuple(row), ("old.pdf", None, None))


if __name__ == "__main__":
    unittest.main()
