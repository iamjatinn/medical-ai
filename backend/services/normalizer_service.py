import re

from services.parser_service import PLAIN_RANGE, RANGE_SEPARATORS, SEX_LABEL

NUMBER = r"\d[\d,]*(?:\.\d+)?"

VALUE_RE = re.compile(rf"^\s*({NUMBER})\s*(.*)$")

# "<0.5 mg/L": a result below (or above) what the lab can measure
QUALIFIED_VALUE_RE = re.compile(rf"^\s*([<>≤≥])=?\s*({NUMBER})\s*(.*)$")

BETWEEN_RE = re.compile(rf"^\s*\(?\s*({NUMBER})\s*(?:{RANGE_SEPARATORS})\s*({NUMBER})")

UPPER_ONLY_RE = re.compile(rf"^\s*(?:[<≤]=?|up\s*to|upto)\s*({NUMBER})", re.IGNORECASE)

# "M: 13.5 - 17.5  F: 12 - 15.5"
SEX_PAIR_RE = re.compile(
    rf"^\s*(?P<l1>{SEX_LABEL})\s*[:\-]?\s*(?P<r1>{PLAIN_RANGE})\s+"
    rf"(?P<l2>{SEX_LABEL})\s*[:\-]?\s*(?P<r2>{PLAIN_RANGE})",
    re.IGNORECASE,
)

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


def parse_result(raw):
    """Like parse_value, but also understands '<0.5 mg/L'.
    Returns (value, unit, qualifier); the qualifier is '<', '>' or ''."""

    match = QUALIFIED_VALUE_RE.match(raw)
    if match:
        qualifier = {"≤": "<", "≥": ">"}.get(match.group(1), match.group(1))
        return _to_float(match.group(2)), match.group(3).strip(), qualifier

    value, unit = parse_value(raw)
    return value, unit, ""


def _pick_for_sex(match, sex):
    """The range for the patient's sex (or the widest one when the sex is unknown)."""

    def is_male(label):
        return label.lower() in ("m", "male", "men")

    ranges = {
        ("M" if is_male(match.group("l1")) else "F"): parse_reference_range(match.group("r1")),
        ("M" if is_male(match.group("l2")) else "F"): parse_reference_range(match.group("r2")),
    }

    if sex in ranges:
        return ranges[sex]

    # sex unknown: use the union, so nobody is flagged because of the wrong sex's range
    lows = [r[0] for r in ranges.values()]
    highs = [r[1] for r in ranges.values()]
    return (None if None in lows else min(lows)), (None if None in highs else max(highs))


def parse_reference_range(raw, sex=None):
    """'13.5 - 17.5' -> (13.5, 17.5), '< 200' -> (None, 200.0),
    '> 40' -> (40.0, None), 'M: 13-17 F: 12-15' -> the range for `sex`.
    Unknown formats -> (None, None)."""

    pair = SEX_PAIR_RE.match(raw)
    if pair:
        return _pick_for_sex(pair, sex)

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


def normalize_report(report, sex=None):

    normalized_report = []

    for test in report:

        value, unit, qualifier = parse_result(test["value"])

        minimum, maximum = parse_reference_range(test["reference_range"], sex)

        normalized_report.append({
            "parameter": test["parameter"],
            "value": value,
            "unit": unit,
            "reference_range": {
                "min": minimum,
                "max": maximum,
            },
            "status": test["status"],
            "qualifier": qualifier,
        })

    return normalized_report
