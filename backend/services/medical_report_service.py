import logging
import os
from pathlib import Path

from config import AI_EXTRACTION_ENABLED
from services.ai_service import explain_report
from services.normalizer_service import normalize_report
from services.parser_service import detect_sex, parse_report
from services.pdf_service import extract_text_from_pdf
from services.report_storage_service import save_report
from services.rule_engine import analyze_report
from services.vision_service import extract_with_ai

logger = logging.getLogger(__name__)

AI_READ_NOTE = (
    "> **Read from an image by AI.** This file had no machine-readable text, so an AI copied "
    "the values from it. Please check them against your original report before relying on them.\n\n"
)


def _ai_note(findings):
    """The warning shown above an AI-read report. A printed flag that disagrees with the
    calculated status is the best sign of a misread digit, so those tests are named."""

    names = [f["parameter"] for f in findings if f.get("status_match") is False]

    if not names:
        return AI_READ_NOTE

    warning = (
        "> The flag printed on the report disagrees with the calculated status for: "
        + ", ".join(names)
        + ". A value may have been misread.\n\n"
    )

    return AI_READ_NOTE.rstrip("\n") + "\n" + warning


def read_results(file_path):
    """Return (rows, sex, read_by_ai).

    Text PDFs go through the exact parser. If that cannot read the file (a scan, a photo,
    or a layout it does not know) the AI copies the printed values instead.
    """

    is_pdf = Path(file_path).suffix.lower() == ".pdf"
    text_error = None

    if is_pdf:
        try:
            text = extract_text_from_pdf(file_path)
            return parse_report(text), detect_sex(text), False
        except ValueError as error:
            text_error = error

    if not AI_EXTRACTION_ENABLED:
        raise text_error or ValueError("Only PDF files can be read without AI.")

    try:
        rows, sex = extract_with_ai(file_path)
        return rows, sex, True

    except ValueError:
        raise                                   # the AI looked and found no lab results

    except Exception:
        logger.exception("AI extraction was not available")
        raise text_error or ValueError("This file could not be read.")


def process_medical_report(file_path, original_filename=None, *, user_id):
    """Run the full pipeline: PDF -> text -> parsed rows -> normalised values
    -> rule-based findings -> AI explanation -> saved report.

    Raises ValueError for problems with the uploaded document itself
    (unreadable PDF, scanned image, no lab results found).
    """

    # Steps 1-2 - Read the results (PDF text + parser, or the AI for scans and photos)
    parsed_report, sex, read_by_ai = read_results(file_path)

    # Step 3 - Normalize values
    normalized_report = normalize_report(parsed_report, sex)

    # Step 4 - Analyze report
    findings = analyze_report(normalized_report)

    if not findings:
        raise ValueError(
            "Lab results were found, but none had a numeric value with a "
            "reference range, so they could not be analysed."
        )

    # Step 5 - Generate the AI explanation (structured JSON + readable text)
    explanation = explain_report(findings)

    if read_by_ai:
        explanation["summary"] = _ai_note(findings) + explanation["summary"]

    # Step 6 - Save report
    report = save_report(
        filename=original_filename or os.path.basename(file_path),
        findings=findings,
        ai_summary=explanation["summary"],
        analysis=explanation["analysis"],
        user_id=user_id,
    )

    # Step 7 - Return response
    return {
        "report_id": report["report_id"],
        "filename": report["filename"],
        "created_at": report["created_at"],
        "findings": report["findings"],
        "ai_summary": report["ai_summary"],
        "analysis": report["analysis"],
    }
