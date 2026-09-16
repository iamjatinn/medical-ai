from services.pdf_service import extract_text_from_pdf
from services.parser_service import parse_report
from services.normalizer_service import normalize_report
from services.rule_engine import analyze_report
from services.ai_service import explain_report
from services.report_storage_service import save_report

import os


def process_medical_report(file_path):

    # Step 1 - Extract PDF text
    text = extract_text_from_pdf(file_path)

    # Step 2 - Parse report
    parsed_report = parse_report(text)

    # Step 3 - Normalize values
    normalized_report = normalize_report(parsed_report)

    # Step 4 - Analyze report
    findings = analyze_report(normalized_report)

    # Step 5 - Generate AI summary
    ai_summary = explain_report(findings)

    # Step 6 - Save report
    report = save_report(
        filename=os.path.basename(file_path),
        findings=findings,
        ai_summary=ai_summary
    )

    # Step 7 - Return response
    return {
        "report_id": report["report_id"],
        "filename": report["filename"],
        "created_at": report["created_at"],
        "findings": report["findings"],
        "ai_summary": report["ai_summary"]
    }