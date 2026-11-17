import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401

from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

import database
from models import db_models  # noqa: F401  (registers the tables)
from models.db_models import ChatMessage, Finding
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

        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)

        self.engine = database.make_engine(f"sqlite:///{Path(folder.name, 'test.db').as_posix()}")
        database.Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)

        patcher = mock.patch.object(
            database, "SessionLocal", sessionmaker(bind=self.engine, expire_on_commit=False)
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_tables_exist(self):
        self.assertEqual(
            set(inspect(self.engine).get_table_names()),
            {"reports", "findings", "chat_messages"},
        )

    def test_save_then_load_round_trip_keeps_order_and_ranges(self):

        saved = storage.save_report("lab.pdf", FINDINGS, "summary text")
        loaded = storage.load_report(saved["report_id"])

        self.assertEqual(loaded["filename"], "lab.pdf")
        self.assertEqual(loaded["ai_summary"], "summary text")
        self.assertEqual([f["parameter"] for f in loaded["findings"]], ["Hemoglobin", "LDL"])
        self.assertEqual(loaded["findings"][1]["reference_range"], {"min": None, "max": 100.0})
        self.assertIsNone(loaded["findings"][1]["status_match"])
        self.assertEqual(loaded["chat_history"], [])

    def test_structured_analysis_is_stored_as_json(self):

        analysis = {"overall_risk": "mild", "abnormal_findings": [{"parameter": "Hemoglobin"}]}

        saved = storage.save_report("lab.pdf", FINDINGS, "summary", analysis=analysis)

        self.assertEqual(storage.load_report(saved["report_id"])["analysis"], analysis)

        # a report saved without analysis (AI failed) still loads
        plain = storage.save_report("lab2.pdf", FINDINGS, "AI is down")
        self.assertIsNone(storage.load_report(plain["report_id"])["analysis"])

    def test_old_table_without_analysis_column_is_migrated(self):
        """The Postgres table created before structured outputs has no
        'analysis' column; init_db() must add it without losing data."""

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

        self.assertNotIn("analysis", {c["name"] for c in inspect(old_engine).get_columns("reports")})

        database.init_db(old_engine)
        database.init_db(old_engine)          # running it twice must be harmless

        self.assertIn("analysis", {c["name"] for c in inspect(old_engine).get_columns("reports")})

        with old_engine.connect() as connection:
            row = connection.exec_driver_sql("SELECT filename, analysis FROM reports").fetchone()

        self.assertEqual(tuple(row), ("old.pdf", None))

    def test_chat_history_is_saved_in_order(self):

        report = storage.save_report("lab.pdf", FINDINGS, "s")

        storage.save_chat(report["report_id"], "first question", "first answer")
        storage.save_chat(report["report_id"], "second question", "second answer")

        history = storage.load_report(report["report_id"])["chat_history"]

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
                storage.load_report(bad_id)

        with self.assertRaises(storage.ReportNotFoundError):
            storage.save_chat("11111111-1111-4111-8111-111111111111", "q", "a")

    def test_deleting_a_report_removes_its_findings_and_messages(self):

        report = storage.save_report("lab.pdf", FINDINGS, "s")
        storage.save_chat(report["report_id"], "q", "a")

        with database.SessionLocal() as session:
            session.delete(session.get(db_models.Report, report["report_id"]))
            session.commit()

            self.assertEqual(session.query(Finding).count(), 0)
            self.assertEqual(session.query(ChatMessage).count(), 0)


if __name__ == "__main__":
    unittest.main()
