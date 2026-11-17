"""Turn the raw text of a lab-report PDF into a list of test records.

No test names or report wording are hard-coded. Two common layouts are
recognised:

1. Row layout     - one test per line:
       Hemoglobin 11.2 g/dL 13.5 - 17.5 Low

2. Cell layout    - every table cell on its own line (what PyMuPDF
   usually produces for tables):
       Hemoglobin
       11.2 g/dL
       13.5 - 17.5
       Low

In the cell layout the *reference range* line is used as the anchor: the
lines before it are the value and the test name, the line after it is the
reported status.
"""

import re

NUMBER = r"\d[\d,]*(?:\.\d+)?"

RANGE = (
    rf"(?:{NUMBER}\s*(?:-|–|—|to)\s*{NUMBER}"
    rf"|[<>≤≥]=?\s*{NUMBER})"
)

STATUS_WORDS = {
    "low": "Low",
    "high": "High",
    "normal": "Normal",
    "abnormal": "Abnormal",
    "borderline": "Borderline",
    "critical": "Critical",
    "l": "Low",
    "h": "High",
    "n": "Normal",
}

STATUS = "|".join(sorted(STATUS_WORDS, key=len, reverse=True))

HEADER_WORDS = {
    "test", "tests", "test name", "investigation", "parameter", "result",
    "results", "value", "reference range", "reference", "ref. range",
    "range", "normal range", "unit", "units", "status", "flag",
}

ROW_RE = re.compile(
    rf"""^
    (?P<parameter>[A-Za-z][A-Za-z0-9 ()/%.,'\-]*?)
    \s+(?P<value>{NUMBER})
    (?:\s*(?P<unit>[^\s\d][^\s]*))?
    \s+(?P<range>{RANGE})
    (?:\s+(?!(?:{STATUS})\s*$)(?P<unit2>[^\s\d][^\s]*))?
    (?:\s+(?P<status>{STATUS}))?
    \s*$""",
    re.IGNORECASE | re.VERBOSE,
)

RANGE_LINE_RE = re.compile(rf"^\s*{RANGE}(?:\s+[^\s\d]\S*)?\s*$")

VALUE_LINE_RE = re.compile(rf"^\s*{NUMBER}(?:\s*[^\s\d]\S*)?\s*$")

UNIT_LINE_RE = re.compile(r"^[^\s\d]\S{0,14}$")


def _clean_status(word):

    return STATUS_WORDS.get(word.strip().lower(), "") if word else ""


def _is_label(line):
    """A line that could be a test name (not a number, not a column header)."""

    return (
        bool(re.match(r"^[A-Za-z]", line))
        and line.strip().lower() not in HEADER_WORDS
        and not RANGE_LINE_RE.match(line)
    )


def _row_records(lines):

    records = []

    for index, line in enumerate(lines):

        match = ROW_RE.match(line)

        if not match:
            continue

        value = f"{match.group('value')} {match.group('unit') or ''}".strip()

        records.append((index, index, {
            "parameter": match.group("parameter").strip(),
            "value": value,
            "reference_range": match.group("range").strip(),
            "status": _clean_status(match.group("status")),
        }))

    return records


def _cell_records(lines, skip):

    records = []

    for index, line in enumerate(lines):

        if index in skip or not RANGE_LINE_RE.match(line):
            continue

        value_line = lines[index - 1] if index >= 1 else ""
        before_value = lines[index - 2] if index >= 2 else ""
        before_unit = lines[index - 3] if index >= 3 else ""

        if VALUE_LINE_RE.match(value_line) and _is_label(before_value):
            value, parameter = value_line, before_value

        elif (
            UNIT_LINE_RE.match(value_line)
            and VALUE_LINE_RE.match(before_value)
            and _is_label(before_unit)
        ):
            # value and unit are on separate lines
            value, parameter = f"{before_value} {value_line}", before_unit

        else:
            continue

        next_line = lines[index + 1] if index + 1 < len(lines) else ""

        records.append((index, index, {
            "parameter": parameter.strip(),
            "value": value.strip(),
            "reference_range": line.strip(),
            "status": _clean_status(next_line),
        }))

    return records


def parse_report(text):
    """Return a list of {parameter, value, reference_range, status} dicts.

    Raises ValueError if no laboratory results can be found, so the API can
    return a clear message instead of crashing.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    row_records = _row_records(lines)

    skip = {index for index, _, _ in row_records}

    cell_records = _cell_records(lines, skip)

    ordered = sorted(row_records + cell_records, key=lambda record: record[0])

    report = [record for _, _, record in ordered]

    if not report:
        raise ValueError(
            "No laboratory results could be found in this PDF. "
            "Upload a text-based lab report with a test name, result and "
            "reference range for each test (scanned images are not supported)."
        )

    return report
