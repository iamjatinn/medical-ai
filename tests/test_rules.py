import unittest

import helpers  # noqa: F401

from services.normalizer_service import (
    normalize_report,
    parse_reference_range,
    parse_value,
)
from services.rule_engine import analyze_report, calculate_status


class NormalizerTests(unittest.TestCase):

    def test_parse_value(self):
        self.assertEqual(parse_value("11.2 g/dL"), (11.2, "g/dL"))
        self.assertEqual(parse_value("9,800 /uL"), (9800.0, "/uL"))
        # not a plain number: kept as text so the rule engine skips it
        self.assertEqual(parse_value("<5 mg/L"), ("<5 mg/L", ""))
        self.assertEqual(parse_value("Positive"), ("Positive", ""))

    def test_parse_reference_range(self):
        self.assertEqual(parse_reference_range("13.5 - 17.5"), (13.5, 17.5))
        self.assertEqual(parse_reference_range("13.5 – 17.5"), (13.5, 17.5))
        self.assertEqual(parse_reference_range("4,000 - 11,000"), (4000.0, 11000.0))
        self.assertEqual(parse_reference_range("< 200"), (None, 200.0))
        self.assertEqual(parse_reference_range("> 40"), (40.0, None))
        self.assertEqual(parse_reference_range("see note"), (None, None))


class RuleEngineTests(unittest.TestCase):

    def test_calculate_status_boundaries(self):
        self.assertEqual(calculate_status(13.5, 13.5, 17.5), "Normal")
        self.assertEqual(calculate_status(17.5, 13.5, 17.5), "Normal")
        self.assertEqual(calculate_status(13.4, 13.5, 17.5), "Low")
        self.assertEqual(calculate_status(17.6, 13.5, 17.5), "High")

    def test_text_values_and_missing_ranges_are_skipped_not_crashed(self):

        report = normalize_report([
            {"parameter": "Urine", "value": "Positive", "reference_range": "Negative", "status": ""},
            {"parameter": "X", "value": "5 mg", "reference_range": "n/a", "status": ""},
            {"parameter": "Hb", "value": "11 g/dL", "reference_range": "13 - 17", "status": "Low"},
        ])

        findings = analyze_report(report)

        self.assertEqual([f["parameter"] for f in findings], ["Hb"])

    def test_status_match_reports_disagreement(self):

        report = normalize_report([
            {"parameter": "Hb", "value": "11 g/dL", "reference_range": "13 - 17", "status": "Normal"},
        ])

        finding = analyze_report(report)[0]

        self.assertEqual(finding["calculated_status"], "Low")
        self.assertFalse(finding["status_match"])


if __name__ == "__main__":
    unittest.main()
