COMPARABLE_STATUSES = {"Low", "High", "Normal"}


def calculate_status(value, minimum, maximum):

    if minimum is not None and value < minimum:
        return "Low"

    if maximum is not None and value > maximum:
        return "High"

    return "Normal"


def calculate_status_for_limit(value, qualifier, minimum, maximum):
    """Status of a result printed with a detection limit ('<0.5' or '>1000').

    The true value is only known to be below (or above) the number, so a status
    is given only when that is enough to decide. Otherwise None (not judged).
    """

    if qualifier == "<":
        if minimum is not None and value <= minimum:
            return "Low"
        if maximum is not None and value > maximum:
            return None
        if minimum is None or minimum <= 0:
            return "Normal"
        return None

    if qualifier == ">":
        if maximum is not None and value >= maximum:
            return "High"
        if minimum is not None and value < minimum:
            return None
        if maximum is None:
            return "Normal"
        return None

    return calculate_status(value, minimum, maximum)


def analyze_report(report):
    """Compare every numeric result with its reference range.

    Results that are not numbers, or that have no usable range, are skipped
    because they cannot be judged by a numeric rule.
    """

    findings = []

    for test in report:

        value = test["value"]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue

        minimum = test["reference_range"]["min"]
        maximum = test["reference_range"]["max"]

        if minimum is None and maximum is None:
            continue

        qualifier = test.get("qualifier") or ""

        if qualifier:
            calculated_status = calculate_status_for_limit(value, qualifier, minimum, maximum)
            if calculated_status is None:
                continue
        else:
            calculated_status = calculate_status(value, minimum, maximum)

        reported_status = test.get("status") or None

        # A report can only disagree with us if it used Low / High / Normal.
        if reported_status in COMPARABLE_STATUSES:
            status_match = reported_status == calculated_status
        else:
            status_match = None

        findings.append({
            "parameter": test["parameter"],
            "value": value,
            "unit": test["unit"],
            "reference_range": test["reference_range"],
            "reported_status": reported_status,
            "calculated_status": calculated_status,
            "status_match": status_match,
            "qualifier": qualifier,
        })

    return findings
