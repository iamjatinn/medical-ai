import json
import uuid
from pathlib import Path
from datetime import datetime

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


def save_report(filename, findings, ai_summary):

    report = {

        "report_id": str(uuid.uuid4()),

        "filename": filename,

        "created_at": datetime.now().isoformat(),

        "findings": findings,

        "ai_summary": ai_summary,

        "chat_history": []
    }

    path = REPORTS_DIR / f"{report['report_id']}.json"

    with open(path, "w", encoding="utf-8") as file:

        json.dump(report, file, indent=4)

    return report


def load_report(report_id):

    path = REPORTS_DIR / f"{report_id}.json"

    with open(path, "r", encoding="utf-8") as file:

        return json.load(file)


def save_chat(report_id, user_message, assistant_message):

    report = load_report(report_id)

    report["chat_history"].append(
        {
            "role": "user",
            "content": user_message
        }
    )

    report["chat_history"].append(
        {
            "role": "assistant",
            "content": assistant_message
        }
    )

    path = REPORTS_DIR / f"{report_id}.json"

    with open(path, "w", encoding="utf-8") as file:

        json.dump(report, file, indent=4)