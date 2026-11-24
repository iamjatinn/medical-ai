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

# What can sit between the two numbers of a range. Besides the plain hyphen and
# the en / em dash, PDF fonts often turn a dash into a minus sign or a middle dot,
# and some labs write "to" or "~".
RANGE_SEPARATORS = "-|–|—|−|‒|·|•|~|to"

# Ranges as printed by real labs:  13 - 17   (13 - 17)   < 200   Up to 5.6
# and one range per sex:  M: 13.5 - 17.5  F: 12 - 15.5
SEX_LABEL = r"(?:male|female|men|women|m|f)"

PLAIN_RANGE = (
    rf"(?:\(?\s*{NUMBER}\s*(?:{RANGE_SEPARATORS})\s*{NUMBER}\s*\)?"
    rf"|[<>≤≥]=?\s*{NUMBER}"
    rf"|(?:up\s*to|upto)\s*{NUMBER})"
)

SEX_RANGE = rf"{SEX_LABEL}\s*[:\-]?\s*{PLAIN_RANGE}\s+{SEX_LABEL}\s*[:\-]?\s*{PLAIN_RANGE}"

RANGE = rf"(?:{SEX_RANGE}|{PLAIN_RANGE})"

# a result printed with a detection limit: "<0.5"
VALUE_NUMBER = rf"(?:[<>≤≥]=?\s*)?{NUMBER}"

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
    (?P<parameter>(?:\d{{1,3}}-)?[A-Za-z][A-Za-z0-9 ()/%.,'\-]*?)
    \s+(?P<value>{VALUE_NUMBER})
    (?:\s*(?P<unit>[^\s\d][^\s]*))?
    \s+(?P<range>{RANGE})
    (?:\s+(?!(?:{STATUS})\s*$)(?P<unit2>[^\s\d][^\s]*))?
    (?:\s+(?P<status>{STATUS}))?
    \s*$""",
    re.IGNORECASE | re.VERBOSE,
)

RANGE_LINE_RE = re.compile(rf"^\s*{RANGE}(?:\s+[^\s\d]\S*)?\s*$", re.IGNORECASE)

VALUE_LINE_RE = re.compile(
    rf"^\s*{VALUE_NUMBER}(?:\s*[^\s\d,.\-–—−‒·•~]\S*)?\s*$"
)

UNIT_LINE_RE = re.compile(r"^[^\s\d]\S{0,14}$")

# "mL/min/1.73m2 > 60": the unit and the range share one line
UNIT_RANGE_LINE_RE = re.compile(
    rf"^(?P<unit>[^\s\d]\S{{0,19}})(?:\s+|(?=[<>≤≥]))(?P<range>{RANGE})\s*$", re.IGNORECASE
)

# "WHITE BLOOD CELL COUNT 10.2": the name and the value share one line
NAME_VALUE_RE = re.compile(
    rf"^(?P<name>(?:\d{{1,3}}-)?[A-Za-z][A-Za-z0-9 ()/%.,'\-]*?)\s+(?P<value>{NUMBER})(?:\s+(?P<flag>{STATUS}))?\s*$",
    re.IGNORECASE,
)

# a line that is only a flag: "L", "H", "High" ...
FLAG_ONLY_RE = re.compile(rf"^(?:{STATUS})$", re.IGNORECASE)

# "15.8 H": a value with the flag letter glued to it
VALUE_FLAG_RE = re.compile(rf"^(?P<value>{NUMBER})\s+(?P<flag>{STATUS})\s*$", re.IGNORECASE)


def _clean_status(word):

    return STATUS_WORDS.get(word.strip().lower(), "") if word else ""


def _is_label(line):
    """A line that could be a test name (not a number, not a column header)."""

    return (
        bool(re.match(r"^(?:\d{1,3}-)?[A-Za-z]", line))
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

        parameter = match.group("parameter").strip()
        status = _clean_status(match.group("status"))

        # "Lymphocyte   L 18 %   20 - 40": a flag letter before the value
        flagged = re.match(r"^(?P<name>.+?)\s+(?P<flag>[LH])$", parameter)
        if flagged and not status:
            parameter, status = flagged.group("name"), _clean_status(flagged.group("flag"))

        records.append((index, index, {
            "parameter": parameter,
            "value": value,
            "reference_range": match.group("range").strip(),
            "status": status,
        }))

    return records


def _cell_records(lines, skip):

    records = []

    for index, line in enumerate(lines):

        if index in skip:
            continue

        unit_range = UNIT_RANGE_LINE_RE.match(line)

        if not (RANGE_LINE_RE.match(line) or unit_range):
            continue

        value_line = lines[index - 1] if index >= 1 else ""
        before_value = lines[index - 2] if index >= 2 else ""
        before_unit = lines[index - 3] if index >= 3 else ""

        range_text = line.strip()
        inline_flag = ""

        if unit_range:
            # value / "unit range" / status
            if not (VALUE_LINE_RE.match(value_line) and _is_label(before_value)):
                continue
            flagged = VALUE_FLAG_RE.match(value_line)
            if flagged:
                value = f"{flagged.group('value')} {unit_range.group('unit')}"
                inline_flag = flagged.group("flag")
            else:
                value = f"{value_line} {unit_range.group('unit')}"
            parameter = before_value
            range_text = unit_range.group("range")

        elif VALUE_LINE_RE.match(value_line) and _is_label(before_value):
            if FLAG_ONLY_RE.match(before_value) and _is_label(before_unit):
                # name / flag / value-with-unit: the flag sits before the value
                value, parameter, inline_flag = value_line, before_unit, before_value
            else:
                value, parameter = value_line, before_value

        elif UNIT_LINE_RE.match(value_line):
            # the unit is on its own line; the value is above it
            flagged = VALUE_FLAG_RE.match(before_value)
            named = NAME_VALUE_RE.match(before_value)

            if VALUE_LINE_RE.match(before_value) and _is_label(before_unit):
                value, parameter = f"{before_value} {value_line}", before_unit
                earlier = lines[index - 4] if index >= 4 else ""
                if FLAG_ONLY_RE.match(before_unit) and _is_label(earlier):
                    # name / flag / value / unit: the flag sits before the value
                    parameter, inline_flag = earlier, before_unit
                if flagged:
                    value = f"{flagged.group('value')} {value_line}"
                    inline_flag = flagged.group("flag")

            elif named:
                # "WHITE BLOOD CELL COUNT 10.2" / "x10^3/uL" / range
                value = f"{named.group('value')} {value_line}"
                parameter = named.group("name")
                inline_flag = named.group("flag") or ""

            else:
                continue

        else:
            continue

        next_line = lines[index + 1] if index + 1 < len(lines) else ""

        records.append((index, index, {
            "parameter": parameter.strip(),
            "value": value.strip(),
            "reference_range": range_text,
            "status": _clean_status(next_line) or _clean_status(inline_flag),
        }))

    return records


_SEX_PATTERNS = [
    re.compile(r"\b(?:gender|sex)\s*[:\-]?\s*(male|female|m|f)\b", re.IGNORECASE),
    re.compile(r"\bage\s*/\s*sex\s*[:\-]?\s*\d+\s*(?:yrs?|years?|y)?\s*/\s*(male|female|m|f)\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*(?:yrs?|years?|y)\s*/\s*(male|female|m|f)\b", re.IGNORECASE),
]


def detect_sex(text):
    """'M' or 'F' from the patient details in the report text, or None.

    Needed because many reports print a different reference range for each sex.
    """

    for pattern in _SEX_PATTERNS:
        match = pattern.search(text)
        if match:
            return "M" if match.group(1).lower().startswith("m") else "F"

    return None


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
