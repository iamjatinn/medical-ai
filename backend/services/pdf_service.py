import fitz

from services.parser_service import parse_report
from services.normalizer_service import normalize_report


def extract_text_from_pdf(pdf_path):

    document = fitz.open(pdf_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    parsed_report = parse_report(text)

    normalized_report = normalize_report(parsed_report)

    return normalized_report