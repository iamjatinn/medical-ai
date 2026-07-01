def parse_report(text):

    # Step 1: Split the text into individual lines and remove empty lines
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Step 2: Find where the actual test data starts
    start = lines.index("Hemoglobin")

    # Step 3: Find where the report ends
    end = lines.index(
        "Doctor's Note: This is a dummy report created for software development and testing only."
    )

    # Step 4: Keep only the medical test records
    test_lines = lines[start:end]

    # Step 5: Store all parsed tests
    report = []

    # Step 6: Read four lines at a time
    for i in range(0, len(test_lines), 4):

        test = {
            "parameter": test_lines[i],
            "value": test_lines[i + 1],
            "reference_range": test_lines[i + 2],
            "status": test_lines[i + 3]
        }

        report.append(test)

    return report