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


class RealWorldVariantTests(unittest.TestCase):
    """Range, value and flag styles found by the second synthetic batch."""

    def analyse(self, text):
        from services.parser_service import detect_sex

        rows = parse_report(text)
        return {f["parameter"]: f for f in analyze_report(normalize_report(rows, detect_sex(text)))}

    def test_up_to_and_bracketed_ranges(self):
        found = self.analyse("LDL 130 mg/dL Up to 100\nGlucose 90 mg/dL (70 - 99)")
        self.assertEqual(found["LDL"]["reference_range"], {"min": None, "max": 100.0})
        self.assertEqual(found["LDL"]["calculated_status"], "High")
        self.assertEqual(found["Glucose"]["calculated_status"], "Normal")

    def test_sex_specific_range_uses_the_patient_sex(self):
        report = "Age / Sex : 27 YRS / {sex}\nHemoglobin 13.0 g/dL M: 13.5 - 17.5 F: 12 - 15.5"
        self.assertEqual(self.analyse(report.format(sex="M"))["Hemoglobin"]["calculated_status"], "Low")
        self.assertEqual(self.analyse(report.format(sex="F"))["Hemoglobin"]["calculated_status"], "Normal")

    def test_unknown_sex_uses_the_widest_range(self):
        found = self.analyse("Hemoglobin 13.0 g/dL Male: 13.5-17.5 Female: 12-15.5")
        self.assertEqual(found["Hemoglobin"]["reference_range"], {"min": 12.0, "max": 17.5})

    def test_sex_is_detected_in_common_headers(self):
        from services.parser_service import detect_sex

        self.assertEqual(detect_sex("Gender: Female"), "F")
        self.assertEqual(detect_sex("Age: 30 Years    Sex: M"), "M")
        self.assertEqual(detect_sex("Age / Sex : 27 YRS / M"), "M")
        self.assertIsNone(detect_sex("no patient details"))

    def test_value_below_detection_limit(self):
        found = self.analyse("CRP <0.5 mg/L < 5")
        self.assertEqual(found["CRP"]["calculated_status"], "Normal")
        self.assertEqual(found["CRP"]["qualifier"], "<")

    def test_undecidable_limit_values_are_not_judged(self):
        # "<10" against a minimum of 12: the true value could be anywhere below 10... that IS low
        self.assertEqual(self.analyse("Ferritin <10 ng/mL 12 - 300")["Ferritin"]["calculated_status"], "Low")
        # "<50" against 12-300: could be low or normal, so it is not judged
        self.assertNotIn("Ferritin", self.analyse("Ferritin <50 ng/mL 12 - 300"))

    def test_flag_before_value_on_one_row(self):
        found = self.analyse("Lymphocyte   L 18 %   20 - 40")
        self.assertIn("Lymphocyte", found)
        self.assertEqual(found["Lymphocyte"]["reported_status"], "Low")

    def test_printed_range_is_not_mistaken_for_a_value(self):
        text = "WBC Count\n3,339 L\ncells/cumm\n4,000-11,000\nCRP\n<0.57\nmg/L\n< 5"
        self.assertEqual(set(self.analyse(text)), {"WBC Count", "CRP"})

    def test_unit_glued_to_range(self):
        self.assertIn("eGFR", self.analyse("eGFR\n85\nmL/min/1.73m2>60"))
