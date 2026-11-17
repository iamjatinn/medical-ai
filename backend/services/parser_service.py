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

RANGE = (
    rf"(?:{NUMBER}\s*(?:{RANGE_SEPARATORS})\s*{NUMBER}"
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
    (?P<parameter>(?:\d{{1,3}}-)?[A-Za-z][A-Za-z0-9 ()/%.,'\-]*?)
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

# "mL/min/1.73m2 > 60": the unit and the range share one line
UNIT_RANGE_LINE_RE = re.compile(
    rf"^(?P<unit>[^\s\d]\S{{0,19}})\s+(?P<range>{RANGE})\s*$"
)

# "WHITE BLOOD CELL COUNT 10.2": the name and the value share one line
NAME_VALUE_RE = re.compile(
    rf"^(?P<name>(?:\d{{1,3}}-)?[A-Za-z][A-Za-z0-9 ()/%.,'\-]*?)\s+(?P<value>{NUMBER})(?:\s+(?P<flag>{STATUS}))?\s*$",
    re.IGNORECASE,
)

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
            value, parameter = value_line, before_value

        elif UNIT_LINE_RE.match(value_line):
            # the unit is on its own line; the value is above it
            flagged = VALUE_FLAG_RE.match(before_value)
            named = NAME_VALUE_RE.match(before_value)

            if VALUE_LINE_RE.match(before_value) and _is_label(before_unit):
                value, parameter = f"{before_value} {value_line}", before_unit
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
