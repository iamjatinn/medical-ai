from services.pdf_service import extract_text_from_pdf
from services.parser_service import parse_report
from services.normalizer_service import normalize_report
from services.rule_engine import analyze_report
from services.ai_service import explain_report

def process_medical_report(file_path):

    text = extract_text_from_pdf(file_path)

    parsed_report = parse_report(text)

    normalized_report = normalize_report(parsed_report)

    analyzed_report = analyze_report(normalized_report)

    findings = analyze_report(normalized_report)

    ai_summary = explain_report(findings)


    return {
    "findings": findings,
    "ai_summary": ai_summary
     }