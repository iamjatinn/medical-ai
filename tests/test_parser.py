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


class SyntheticReportRegressionTests(unittest.TestCase):
    """Layouts found by the randomised report generator (evals/generate_reports.py)."""

    def parse(self, text):
        return {r["parameter"]: r for r in parse_report(text)}

    def test_range_with_middle_dot_or_minus_sign(self):
        for sep in ("·", "−", "–", "to"):
            rows = parse_report(f"Hemoglobin 11.2 g/dL 13.5 {sep} 17.5 Low")
            self.assertEqual(rows[0]["reference_range"], f"13.5 {sep} 17.5")
            self.assertEqual(normalize_report(rows)[0]["reference_range"], {"min": 13.5, "max": 17.5})

    def test_name_starting_with_digits(self):
        rows = self.parse("25-OH Vitamin D   134 ng/mL   30 - 100")
        self.assertIn("25-OH Vitamin D", rows)

    def test_unit_with_digits_shares_line_with_range(self):
        rows = self.parse("eGFR\n68\nmL/min/1.73m2 > 60")
        self.assertEqual(rows["eGFR"]["value"], "68 mL/min/1.73m2")
        self.assertEqual(rows["eGFR"]["reference_range"], "> 60")

    def test_name_and_value_on_one_line_unit_below(self):
        rows = self.parse("WHITE BLOOD CELL COUNT 10.2\nx10^3/uL\n4 - 11")
        self.assertEqual(rows["WHITE BLOOD CELL COUNT"]["value"], "10.2 x10^3/uL")

    def test_flag_glued_to_value_is_not_part_of_the_unit(self):
        rows = self.parse("Glycated Hemoglobin (HbA1c) 3.5 L\n%\n4 - 5.6")
        record = rows["Glycated Hemoglobin (HbA1c)"]
        self.assertEqual(record["value"], "3.5 %")
        self.assertEqual(record["status"], "Low")

        rows = self.parse("eGFR\n47 L\nmL/min/1.73m2 > 60")
        self.assertEqual(rows["eGFR"]["value"], "47 mL/min/1.73m2")


class FlagBeforeValueTests(unittest.TestCase):
    """Found with a real CBC report: name, flag, value, unit, range - one per line."""

    def test_flag_between_name_and_value(self):
        text = (
            "NEUTROPHILS\n79\n%\n40 - 80\n"
            "LYMPHOCYTE\nL\n18\n%\n20 - 40\n"
            "MEAN CELL HAEMOGLOBIN CON, MCHC\nH\n35.7\n%\n31.5 - 34.5\n"
        )
        rows = {r["parameter"]: r for r in parse_report(text)}
        self.assertEqual(set(rows), {"NEUTROPHILS", "LYMPHOCYTE", "MEAN CELL HAEMOGLOBIN CON, MCHC"})
        self.assertEqual(rows["LYMPHOCYTE"]["value"], "18 %")
        self.assertEqual(rows["LYMPHOCYTE"]["status"], "Low")
        self.assertEqual(rows["MEAN CELL HAEMOGLOBIN CON, MCHC"]["status"], "High")
        self.assertEqual(rows["NEUTROPHILS"]["status"], "")
