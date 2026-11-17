"""Score the lab-report pipeline against synthetic reports with known answers.

Stage 1  PARSING   (no API, fast)
         PDF -> text -> parse -> normalise -> Low/Normal/High, compared with the
         answer key of every report in evals/synthetic/. Reported per layout:
         tests found, values/units/ranges right, status right.

Stage 2  KNOWLEDGE COVERAGE (real embedding model, no API)
         For every truly abnormal test in the answer keys: does the search find
         a page that explains it, when searching the way the app does?

Generate the reports first:
    backend\\venv\\Scripts\\python evals\\generate_reports.py --count 120 --seed 7
Then:
    backend\\venv\\Scripts\\python evals\\pipeline_eval.py            # both stages
    backend\\venv\\Scripts\\python evals\\pipeline_eval.py --stage parse -v
"""

import argparse
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
sys.path.insert(0, str(HERE))

logging.disable(logging.CRITICAL)

from lab_catalogue import CATALOGUE  # noqa: E402
from services.normalizer_service import normalize_report  # noqa: E402
from services.parser_service import parse_report  # noqa: E402
from services.pdf_service import extract_text_from_pdf  # noqa: E402
from services.rule_engine import analyze_report  # noqa: E402


def norm_name(text):
    return re.sub(r"\s+", " ", str(text)).strip().casefold()


def norm_unit(text):
    return str(text or "").replace("µ", "u").strip()


def close(a, b):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


# ------------------------------------------------------------------ stage 1 ---

def run_pipeline(pdf_path):
    """What the app does before it calls the AI. Returns (outcome, findings, parsed_names)."""

    try:
        text = extract_text_from_pdf(pdf_path)
    except ValueError as error:
        return "unreadable", [], set(), str(error)

    try:
        rows = parse_report(text)
    except ValueError as error:
        return "no_results", [], set(), str(error)

    findings = analyze_report(normalize_report(rows))

    return "ok", findings, {norm_name(r["parameter"]) for r in rows}, ""


def score_report(key, findings, parsed_names):
    """Compare one report's findings with its answer key."""

    by_name = {}
    for finding in findings:
        by_name.setdefault(norm_name(finding["parameter"]), finding)

    results, matched = [], set()

    for test in key["tests"]:

        name = norm_name(test["printed_name"])
        finding = by_name.get(name)
        problems = []

        if finding is None:
            problems.append("parsed_but_dropped" if name in parsed_names else "not_parsed")
        else:
            matched.add(name)

            if not close(finding["value"], test["value"]):
                problems.append("wrong_value")
            if norm_unit(finding["unit"]) != norm_unit(test["unit"]):
                problems.append("wrong_unit")
            if not (close(finding["reference_range"]["min"], test["min"])
                    and close(finding["reference_range"]["max"], test["max"])):
                problems.append("wrong_range")
            if finding["calculated_status"] != test["expected_status"]:
                problems.append("wrong_status")

        results.append({"test": test, "finding": finding, "problems": problems})

    extras = [f for f in findings if norm_name(f["parameter"]) not in matched]

    return results, extras


def stage_parse(directory, verbose):

    keys = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("report_*.json"))]

    if not keys:
        sys.exit(f"No reports in {directory}. Run evals/generate_reports.py first.")

    layouts = defaultdict(lambda: Counter())
    problems_total = Counter()
    examples = defaultdict(list)
    report_rows = []

    for key in keys:

        outcome, findings, parsed_names, message = run_pipeline(directory / key["file"])
        row = layouts[key["layout"]]
        row["reports"] += 1

        if not key["expect_readable"]:
            # a scanned image: the right behaviour is a clear refusal, not a crash or junk
            row["graceful_refusal"] += outcome in ("unreadable", "no_results")
            report_rows.append({"file": key["file"], "layout": key["layout"], "outcome": outcome})
            continue

        results, extras = score_report(key, findings, parsed_names)

        row["tests"] += len(results)
        row["found"] += sum(1 for r in results if r["finding"] is not None)
        row["perfect_tests"] += sum(1 for r in results if not r["problems"])
        row["status_right"] += sum(1 for r in results if r["finding"] and "wrong_status" not in r["problems"])
        row["extras"] += len(extras)
        row["perfect_reports"] += all(not r["problems"] for r in results) and not extras

        for r in results:
            for problem in r["problems"]:
                problems_total[problem] += 1
                if len(examples[(key["layout"], problem)]) < 2:
                    t, f = r["test"], r["finding"]
                    got = "-" if f is None else f"{f['value']} {f['unit']!r} {f['reference_range']} {f['calculated_status']}"
                    examples[(key["layout"], problem)].append(
                        f"{key['file']}: {t['printed_name']} expected {t['value']} {t['unit']!r} "
                        f"[{t['min']}, {t['max']}] {t['expected_status']}  ->  got {got}")

        for f in extras:
            problems_total["extra_finding"] += 1
            if len(examples[(key["layout"], "extra_finding")]) < 2:
                examples[(key["layout"], "extra_finding")].append(
                    f"{key['file']}: not in the answer key: {f['parameter']!r} = {f['value']}")

        report_rows.append({"file": key["file"], "layout": key["layout"], "outcome": outcome,
                            "perfect": all(not r["problems"] for r in results) and not extras})

    # ---- print ----
    print(f"\nSTAGE 1: parsing  |  {len(keys)} synthetic reports in {directory.name}/\n")
    print(f"{'layout':<20}{'reports':>8}{'tests':>7}{'found':>8}{'all-right':>11}{'status':>9}{'extras':>8}{'perfect rpt':>13}")

    total = Counter()
    for layout, row in sorted(layouts.items()):
        total.update(row)
        if row["tests"]:
            print(f"{layout:<20}{row['reports']:>8}{row['tests']:>7}"
                  f"{row['found'] / row['tests']:>8.0%}{row['perfect_tests'] / row['tests']:>11.0%}"
                  f"{row['status_right'] / row['tests']:>9.0%}{row['extras']:>8}"
                  f"{row['perfect_reports'] / row['reports']:>13.0%}")
        else:
            print(f"{layout:<20}{row['reports']:>8}   (image only) clear refusal: "
                  f"{row['graceful_refusal']}/{row['reports']}")

    print(f"{'ALL TEXT REPORTS':<20}{sum(l['reports'] for n, l in layouts.items() if l['tests']):>8}"
          f"{total['tests']:>7}{total['found'] / max(1, total['tests']):>8.0%}"
          f"{total['perfect_tests'] / max(1, total['tests']):>11.0%}{total['status_right'] / max(1, total['tests']):>9.0%}"
          f"{total['extras']:>8}")

    if problems_total:
        print("\nProblems by type:", dict(problems_total.most_common()))

    shown = 0
    for (layout, problem), lines in sorted(examples.items()):
        if shown >= (60 if verbose else 14):
            break
        print(f"\n  [{layout}] {problem}")
        for line in lines:
            print("    " + line[:230])
        shown += 1

    return {"layouts": {k: dict(v) for k, v in layouts.items()}, "problems": dict(problems_total),
            "reports": report_rows}


# ------------------------------------------------------------------ stage 2 ---

def stage_retrieval(directory):

    from config import MIN_SIMILARITY, TOP_K  # noqa: E402
    from services.index_builder import build_index  # noqa: E402
    from services.query_builder import build_query  # noqa: E402

    rag = build_index()

    keys = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("report_*.json"))]

    seen = set()
    rows = []

    for key in keys:
        for test in key["tests"]:

            if test["expected_status"] == "Normal":
                continue

            # the app searches with "<name as printed> <status> meaning causes ..."
            query = build_query({"parameter": test["printed_name"], "calculated_status": test["expected_status"]})

            if (query, test["key"]) in seen:
                continue
            seen.add((query, test["key"]))

            wanted = set(CATALOGUE[test["key"]]["docs"])
            got = [r["source"].get("name") for r in rag.search(query, k=TOP_K, min_score=MIN_SIMILARITY)]

            rows.append({"key": test["key"], "name": test["printed_name"], "status": test["expected_status"],
                         "hit": bool(wanted & set(got)), "got": got})

    hits = sum(r["hit"] for r in rows)

    print(f"\nSTAGE 2: does the knowledge base explain each abnormal test?  "
          f"({len(rows)} distinct abnormal tests, top-{TOP_K}, threshold {MIN_SIMILARITY})\n")
    print(f"coverage: {hits}/{len(rows)} = {hits / max(1, len(rows)):.0%}")

    by_key = defaultdict(lambda: [0, 0])
    for r in rows:
        by_key[r["key"]][1] += 1
        by_key[r["key"]][0] += r["hit"]

    weak = sorted((k for k, (h, n) in by_key.items() if h < n), key=lambda k: by_key[k][0] / by_key[k][1])

    if weak:
        print("\nTests whose explanation page is sometimes NOT retrieved:")
        for k in weak:
            h, n = by_key[k]
            misses = [f"{r['name']} {r['status']} -> {[g.replace('mplus_', '') for g in r['got']][:2] or 'nothing'}"
                      for r in rows if r["key"] == k and not r["hit"]][:2]
            print(f"  {k:<14}{h}/{n}   e.g. " + "; ".join(misses))

    return {"coverage": hits / max(1, len(rows)), "tests": len(rows), "rows": rows}


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=str(HERE / "synthetic"))
    parser.add_argument("--stage", choices=["parse", "retrieval", "all"], default="all")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    directory = Path(args.dir)
    result = {"date": datetime.now().isoformat(timespec="seconds")}

    if args.stage in ("parse", "all"):
        result["parse"] = stage_parse(directory, args.verbose)

    if args.stage in ("retrieval", "all"):
        result["retrieval"] = stage_retrieval(directory)

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "pipeline.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print("\nSaved evals/results/pipeline.json")


if __name__ == "__main__":
    main()
