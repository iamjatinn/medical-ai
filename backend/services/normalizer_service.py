import re

from services.parser_service import RANGE_SEPARATORS

NUMBER = r"\d[\d,]*(?:\.\d+)?"

VALUE_RE = re.compile(rf"^\s*({NUMBER})\s*(.*)$")

BETWEEN_RE = re.compile(rf"^\s*({NUMBER})\s*(?:{RANGE_SEPARATORS})\s*({NUMBER})")

UPPER_ONLY_RE = re.compile(rf"^\s*[<≤]=?\s*({NUMBER})")

LOWER_ONLY_RE = re.compile(rf"^\s*[>≥]=?\s*({NUMBER})")


def _to_float(text):

    return float(text.replace(",", ""))


def parse_value(raw):
    """'11.2 g/dL' -> (11.2, 'g/dL').  Anything that is not a plain number
    (for example '<5' or 'Positive') is kept as text and skipped later."""

    match = VALUE_RE.match(raw)

    if match:
        return _to_float(match.group(1)), match.group(2).strip()

    return raw, ""


def parse_reference_range(raw):
    """'13.5 - 17.5' -> (13.5, 17.5), '< 200' -> (None, 200.0),
    '> 40' -> (40.0, None).  Unknown formats -> (None, None)."""

    match = BETWEEN_RE.match(raw)
    if match:
        return _to_float(match.group(1)), _to_float(match.group(2))

    match = UPPER_ONLY_RE.match(raw)
    if match:
        return None, _to_float(match.group(1))

    match = LOWER_ONLY_RE.match(raw)
    if match:
        return _to_float(match.group(1)), None

    return None, None


def normalize_report(report):

    normalized_report = []

    for test in report:

        value, unit = parse_value(test["value"])

        minimum, maximum = parse_reference_range(test["reference_range"])

        normalized_report.append({
            "parameter": test["parameter"],
            "value": value,
            "unit": unit,
            "reference_range": {
                "min": minimum,
                "max": maximum,
            },
            "status": test["status"],
        })

    return normalized_report
