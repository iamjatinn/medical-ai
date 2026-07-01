import re


def normalize_report(report):

    normalized_report = []

    for test in report:

        # Extract numeric value and unit
        value_match = re.match(r"([\d.]+)\s*(.*)", test["value"])

        if value_match:
            value = float(value_match.group(1))
            unit = value_match.group(2)
        else:
            value = test["value"]
            unit = ""

        # Extract reference range
        range_match = re.match(r"([\d.]+)\s*-\s*([\d.]+)", test["reference_range"])

        if range_match:
            min_range = float(range_match.group(1))
            max_range = float(range_match.group(2))
        else:
            min_range = None
            max_range = None

        normalized_report.append({
            "parameter": test["parameter"],
            "value": value,
            "unit": unit,
            "reference_range": {
                "min": min_range,
                "max": max_range
            },
            "status": test["status"]
        })

    return normalized_report