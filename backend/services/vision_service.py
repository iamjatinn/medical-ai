"""Read a lab report that has no text layer (a scan or a photo) with Gemini.

The normal path (PDF text -> parser) is exact and free, so it is always tried
first. This is the fallback for what it cannot read: scanned PDFs, photos or
screenshots of a report, and layouts the parser does not understand.

The AI is used ONLY to copy what is printed (name, value, unit, range, flag).
It does not judge anything: the Low/Normal/High status is still calculated by the
rule engine from the copied numbers, exactly as for a text PDF.
"""

import logging
from pathlib import Path
from typing import List, Literal

from google.genai import types
from pydantic import BaseModel

from config import MAX_EXTRACTED_TESTS
from services.gemini_service import generate_structured
from services.parser_service import _clean_status

logger = logging.getLogger(__name__)

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

EXTRACTION_PROMPT = """You are reading a laboratory report (a scan, a photo or a PDF).
Copy the test results EXACTLY as printed. Do not interpret, correct, convert or
calculate anything, and do not add tests that are not on the page.

For every test result that has a measured value:
- name: the test name as printed
- value: the result as printed, e.g. "11.2" or "<0.5" (numbers only, no unit)
- unit: the unit as printed, or "" if none
- reference_range: the reference range exactly as printed, e.g. "13.5 - 17.5", "< 200",
  "Male: 13.5-17.5 Female: 12-15.5". Use "" if none is printed.
- flag: the flag printed next to the result (L, H, Low, High, ...), or "" if none

Also give patient_sex ("M" or "F") only if the report states it, otherwise "unknown".
Skip anything you cannot read clearly rather than guessing. Skip results that have no
number (for example "Positive" or "Negative")."""


class ExtractedTest(BaseModel):
    name: str
    value: str
    unit: str = ""
    reference_range: str = ""
    flag: str = ""


class ExtractedReport(BaseModel):
    patient_sex: Literal["M", "F", "unknown"] = "unknown"
    tests: List[ExtractedTest]


def extract_with_ai(file_path):
    """Return (rows, sex) in the same shape as parse_report() / detect_sex().

    Raises ValueError if the file has no readable lab results and RuntimeError if
    the AI itself is unavailable.
    """

    path = Path(file_path)
    mime_type = MIME_TYPES.get(path.suffix.lower())

    if mime_type is None:
        raise ValueError("Only PDF, PNG and JPG files can be read.")

    logger.info("Reading %s with the AI (no usable text layer)", path.name)

    contents = [types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type), EXTRACTION_PROMPT]

    extracted, error = generate_structured(contents, ExtractedReport)

    if extracted is None:
        raise RuntimeError(error)

    rows = []

    for test in extracted.tests[:MAX_EXTRACTED_TESTS]:

        name, value = test.name.strip(), test.value.strip()

        if not name or not value:
            continue

        rows.append({
            "parameter": name,
            "value": f"{value} {test.unit.strip()}".strip(),
            "reference_range": test.reference_range.strip(),
            "status": _clean_status(test.flag),
        })

    if not rows:
        raise ValueError(
            "No laboratory results could be read from this file. Try a clearer "
            "photo or scan, or a text-based PDF."
        )

    sex = None if extracted.patient_sex == "unknown" else extracted.patient_sex

    return rows, sex
