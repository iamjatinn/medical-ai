def analyze_report(report):

    findings = []

    for test in report:

        value = test["value"]
        minimum = test["reference_range"]["min"]
        maximum = test["reference_range"]["max"]

        if minimum is None or maximum is None:
            continue

        if value < minimum:
            calculated_status = "Low"

        elif value > maximum:
            calculated_status = "High"

        else:
            calculated_status = "Normal"

        findings.append({
            "parameter": test["parameter"],
            "value": value,
            "unit": test["unit"],
            "reference_range": test["reference_range"],
            "reported_status": test["status"],
            "calculated_status": calculated_status,
            "status_match": calculated_status == test["status"]
        })

    return findings