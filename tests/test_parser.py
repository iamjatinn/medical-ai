import unittest

import helpers  # noqa: F401  (sets up sys.path)
import pymupdf

from services.normalizer_service import normalize_report
from services.parser_service import parse_report
from services.rule_engine import analyze_report


def analyse(text):
    return analyze_report(normalize_report(parse_report(text)))


class ParserTests(unittest.TestCase):

    def test_sample_pdf_gives_six_correct_findings(self):

        text = "".join(page.get_text() for page in pymupdf.open(str(helpers.SAMPLE_PDF)))

        findings = analyse(text)

        self.assertEqual(
            [(f["parameter"], f["calculated_status"]) for f in findings],
            [
                ("Hemoglobin", "Low"),
                ("WBC", "Normal"),
                ("RBC", "Low"),
                ("Platelets", "Normal"),
                ("Glucose (Fasting)", "High"),
                ("Vitamin D", "Low"),
            ],
        )

        self.assertTrue(all(f["status_match"] for f in findings))

    def test_one_test_per_line_layout(self):

        findings = analyse(
            "Hemoglobin 11.2 g/dL 13.5 - 17.5 Low\n"
            "WBC 9,800 /uL 4000 - 11000 Normal\n"
            "HbA1c 5.4 % 4.0 - 5.6\n"
            "Glucose (Fasting) 145 mg/dL 70 - 99 mg/dL H\n"
        )

        by_name = {f["parameter"]: f for f in findings}

        self.assertEqual(by_name["Hemoglobin"]["reported_status"], "Low")
        self.assertEqual(by_name["WBC"]["value"], 9800.0)
        self.assertIsNone(by_name["HbA1c"]["reported_status"])
        self.assertIsNone(by_name["HbA1c"]["status_match"])
        self.assertEqual(by_name["Glucose (Fasting)"]["reported_status"], "High")

    def test_value_and_unit_on_separate_lines(self):

        findings = analyse(
            "Test\nResult\nUnit\nReference Range\nStatus\n"
            "Creatinine\n1.9\nmg/dL\n0.7 - 1.3\nHigh\n"
        )

        self.assertEqual(findings[0]["parameter"], "Creatinine")
        self.assertEqual(findings[0]["unit"], "mg/dL")
        self.assertEqual(findings[0]["calculated_status"], "High")

    def test_one_sided_ranges(self):

        findings = analyse(
            "Total Cholesterol 210 mg/dL < 200 High\n"
            "HDL 38 mg/dL > 40 Low\n"
            "LDL 90 mg/dL < 100\n"
        )

        self.assertEqual(
            [f["calculated_status"] for f in findings],
            ["High", "Low", "Normal"],
        )

    def test_document_without_results_raises_clear_error(self):

        with self.assertRaises(ValueError) as context:
            parse_report("Dear patient,\nPlease visit us again.\nAge: 35")

        self.assertIn("No laboratory results", str(context.exception))


if __name__ == "__main__":
    unittest.main()
