"""Save and load reports and chat history in the database.

Same functions and return shapes as the old JSON-file version, so the rest
of the app did not have to change.
"""

import uuid

import database
from models.db_models import ChatMessage, Finding, Report


class ReportNotFoundError(Exception):
    """Raised when a report id is malformed or no such report exists."""


def _clean_id(report_id) -> str:
    """The id must be a real UUID (this also rejects things like '../../x')."""

    try:
        return str(uuid.UUID(str(report_id)))
    except ValueError as error:
        raise ReportNotFoundError(report_id) from error


def _to_dict(report: Report) -> dict:

    return {
        "report_id": report.id,
        "filename": report.filename,
        "created_at": report.created_at.isoformat(),
        "findings": [
            {
                "parameter": f.parameter,
                "value": f.value,
                "unit": f.unit,
                "reference_range": {"min": f.ref_min, "max": f.ref_max},
                "reported_status": f.reported_status,
                "calculated_status": f.calculated_status,
                "status_match": f.status_match,
            }
            for f in report.findings
        ],
        "ai_summary": report.ai_summary,
        "analysis": report.analysis,
        "chat_history": [
            {"role": m.role, "content": m.content} for m in report.messages
        ],
    }


def save_report(filename, findings, ai_summary, analysis=None):

    report = Report(
        id=str(uuid.uuid4()),
        filename=filename[:255],
        ai_summary=ai_summary,
        analysis=analysis,
        findings=[
            Finding(
                position=position,
                parameter=finding["parameter"],
                value=finding["value"],
                unit=finding.get("unit", ""),
                ref_min=finding["reference_range"]["min"],
                ref_max=finding["reference_range"]["max"],
                reported_status=finding.get("reported_status"),
                calculated_status=finding["calculated_status"],
                status_match=finding.get("status_match"),
            )
            for position, finding in enumerate(findings)
        ],
    )

    with database.SessionLocal() as session:
        session.add(report)
        session.commit()
        session.refresh(report)
        return _to_dict(report)


def load_report(report_id):

    with database.SessionLocal() as session:

        report = session.get(Report, _clean_id(report_id))

        if report is None:
            raise ReportNotFoundError(report_id)

        return _to_dict(report)


def save_chat(report_id, user_message, assistant_message):

    report_id = _clean_id(report_id)

    with database.SessionLocal() as session:

        if session.get(Report, report_id) is None:
            raise ReportNotFoundError(report_id)

        session.add_all([
            ChatMessage(report_id=report_id, role="user", content=user_message),
            ChatMessage(report_id=report_id, role="assistant", content=assistant_message),
        ])

        session.commit()
