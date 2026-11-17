import json
import os
import threading
import uuid
from datetime import datetime

from config import REPORTS_DIR

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()


class ReportNotFoundError(Exception):
    """Raised when a report id is malformed or no such report exists."""


def _report_path(report_id: str):
    """Build the path for a report id. The id must be a real UUID, which
    also blocks path-traversal ids such as '../../secret'."""

    try:
        clean_id = str(uuid.UUID(str(report_id)))
    except ValueError as error:
        raise ReportNotFoundError(report_id) from error

    return REPORTS_DIR / f"{clean_id}.json"


def _write(path, report):
    """Write atomically so a crash cannot leave a half-written JSON file."""

    temp_path = path.with_suffix(".json.tmp")

    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    os.replace(temp_path, path)


def save_report(filename, findings, ai_summary):

    report = {
        "report_id": str(uuid.uuid4()),
        "filename": filename,
        "created_at": datetime.now().isoformat(),
        "findings": findings,
        "ai_summary": ai_summary,
        "chat_history": [],
    }

    with _lock:
        _write(_report_path(report["report_id"]), report)

    return report


def load_report(report_id):

    path = _report_path(report_id)

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as error:
        raise ReportNotFoundError(report_id) from error


def save_chat(report_id, user_message, assistant_message):

    with _lock:

        report = load_report(report_id)

        report["chat_history"].append({"role": "user", "content": user_message})
        report["chat_history"].append({"role": "assistant", "content": assistant_message})

        _write(_report_path(report_id), report)
