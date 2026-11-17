COMPARABLE_STATUSES = {"Low", "High", "Normal"}


def calculate_status(value, minimum, maximum):

    if minimum is not None and value < minimum:
        return "Low"

    if maximum is not None and value > maximum:
        return "High"

    return "Normal"


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
        })

    return findings
