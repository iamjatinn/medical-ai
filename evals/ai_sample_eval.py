"""Run the full pipeline INCLUDING the live AI on a few synthetic reports.

Checks each answer against the report's answer key:
  - the AI returned a valid structured analysis (API errors are reported as ERROR, not as failures)
  - it explains exactly the truly abnormal tests (none missing, none invented, right Low/High)
  - sources are attached when something is abnormal
  - overall risk is "low" when nothing is abnormal

    backend\venv\Scripts\python evals\ai_sample_eval.py --n 8 --seed 1
Uses Gemini quota: about one call per report.
"""

import argparse
import json
import logging
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
logging.disable(logging.CRITICAL)

from services.ai_service import explain_report  # noqa: E402
from services.normalizer_service import normalize_report  # noqa: E402
from services.parser_service import parse_report  # noqa: E402
from services.pdf_service import extract_text_from_pdf  # noqa: E402
from services.rule_engine import analyze_report  # noqa: E402


def norm(text):
    return " ".join(str(text).split()).casefold()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(HERE / "synthetic_holdout"))
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    keys = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(args.dir).glob("report_*.json"))]
    keys = [k for k in keys if k["expect_readable"]]
    random.Random(args.seed).shuffle(keys)

    rows = []
    for key in keys[: args.n]:
        findings = analyze_report(normalize_report(parse_report(extract_text_from_pdf(Path(args.dir) / key["file"]))))
        result = explain_report(findings)
        analysis = result["analysis"]
        expected = {norm(t["printed_name"]): t["expected_status"] for t in key["tests"] if t["expected_status"] != "Normal"}

        row = {"file": key["file"], "abnormal": len(expected)}
        if analysis is None:
            row.update(verdict="ERROR", note=result["summary"][:120])
        else:
            got = {norm(a["parameter"]): a["status"] for a in analysis["abnormal_findings"]}
            problems = []
            if set(expected) - set(got):
                problems.append(f"missing {sorted(set(expected) - set(got))}")
            if set(got) - set(expected):
                problems.append(f"invented {sorted(set(got) - set(expected))}")
            wrong = [k for k in set(got) & set(expected) if got[k] != expected[k]]
            if wrong:
                problems.append(f"wrong direction {wrong}")
            if expected and not analysis["sources"]:
                problems.append("no sources")
            if not expected and analysis["overall_risk"] != "low":
                problems.append(f"risk {analysis['overall_risk']} but nothing abnormal")
            row.update(verdict="PASS" if not problems else "FAIL", note="; ".join(problems),
                       risk=analysis["overall_risk"], sources=len(analysis["sources"]))
        rows.append(row)
        print(f"{row['verdict']:<6}{row['file']:<38}abnormal={row['abnormal']:<3}{row.get('note', '')}", flush=True)

    scored = [r for r in rows if r["verdict"] != "ERROR"]
    print(f"\n{sum(r['verdict'] == 'PASS' for r in scored)}/{len(scored)} passed, "
          f"{len(rows) - len(scored)} API errors (not counted)")
    (HERE / "results" / "ai_sample.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
