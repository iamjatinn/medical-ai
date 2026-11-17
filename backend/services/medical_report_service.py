import os

from services.ai_service import explain_report
from services.normalizer_service import normalize_report
from services.parser_service import parse_report
from services.pdf_service import extract_text_from_pdf
from services.report_storage_service import save_report
from services.rule_engine import analyze_report


def process_medical_report(file_path, original_filename=None):
    """Run the full pipeline: PDF -> text -> parsed rows -> normalised values
    -> rule-based findings -> AI explanation -> saved report.

    Raises ValueError for problems with the uploaded document itself
    (unreadable PDF, scanned image, no lab results found).
    """

    # Step 1 - Extract PDF text
    text = extract_text_from_pdf(file_path)

    # Step 2 - Parse report
    parsed_report = parse_report(text)

    # Step 3 - Normalize values
    normalized_report = normalize_report(parsed_report)

    # Step 4 - Analyze report
    findings = analyze_report(normalized_report)

    if not findings:
        raise ValueError(
            "Lab results were found, but none had a numeric value with a "
            "reference range, so they could not be analysed."
        )

    # Step 5 - Generate the AI explanation (structured JSON + readable text)
    explanation = explain_report(findings)

    # Step 6 - Save report
    report = save_report(
        filename=original_filename or os.path.basename(file_path),
        findings=findings,
        ai_summary=explanation["summary"],
        analysis=explanation["analysis"],
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
