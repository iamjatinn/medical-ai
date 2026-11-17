"""Save and load reports and chat history in the database.

Every function takes the OWNER's user_id and puts it into the database query
itself ("WHERE id = ... AND user_id = ..."). A report that belongs to someone
else is therefore indistinguishable from one that does not exist, so a user can
neither read nor probe other people's reports.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

import database
from models.db_models import ChatMessage, Finding, Report


class ReportNotFoundError(Exception):
    """Raised when a report id is malformed, does not exist, or is not yours."""


def _clean_id(report_id) -> str:
    """The id must be a real UUID (this also rejects things like '../../x')."""

    try:
        return str(uuid.UUID(str(report_id)))
    except ValueError as error:
        raise ReportNotFoundError(report_id) from error


def _owned_report(session, report_id: str, user_id: int):
    """The report with this id AND this owner, or None."""

    return session.scalar(
        select(Report).where(Report.id == _clean_id(report_id), Report.user_id == user_id)
    )


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


def save_report(filename, findings, ai_summary, analysis=None, *, user_id):

    report = Report(
        id=str(uuid.uuid4()),
        user_id=user_id,
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


def load_report(report_id, *, user_id):

    with database.SessionLocal() as session:

        report = _owned_report(session, report_id, user_id)

        if report is None:
            raise ReportNotFoundError(report_id)

        return _to_dict(report)


def save_chat(report_id, user_message, assistant_message, *, user_id):

    with database.SessionLocal() as session:

        report = _owned_report(session, report_id, user_id)

        if report is None:
            raise ReportNotFoundError(report_id)

        session.add_all([
            ChatMessage(report_id=report.id, role="user", content=user_message),
            ChatMessage(report_id=report.id, role="assistant", content=assistant_message),
        ])

        session.commit()


def list_reports(*, user_id, limit: int = 50):
    """The user's reports, newest first (without the long texts)."""

    with database.SessionLocal() as session:

        reports = session.scalars(
            select(Report)
            .where(Report.user_id == user_id)
            .options(selectinload(Report.findings))
            .order_by(Report.created_at.desc())
            .limit(limit)
        ).all()

        return [
            {
                "report_id": r.id,
                "filename": r.filename,
                "created_at": r.created_at.isoformat(),
                "overall_risk": (r.analysis or {}).get("overall_risk"),
                "abnormal_count": sum(1 for f in r.findings if f.calculated_status != "Normal"),
            }
            for r in reports
        ]


def delete_report(report_id, *, user_id):

    with database.SessionLocal() as session:

        report = _owned_report(session, report_id, user_id)

        if report is None:
            raise ReportNotFoundError(report_id)

        session.delete(report)        # findings and chat messages are deleted with it
        session.commit()
