"""Live test of the AI reader: scanned (image-only) synthetic reports vs their answer keys.

The synthetic 'scanned' reports have no text layer, so the normal parser cannot read them
and the app falls back to Gemini. The AI only copies the printed values; the status is
calculated by the rules. Scoring is the same as for text reports (pipeline_eval).

    backend\venv\Scripts\python evals\scan_eval.py --n 10
Uses Gemini quota: one call per report.
"""

import argparse
import json
import logging
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
sys.path.insert(0, str(HERE))
logging.disable(logging.CRITICAL)

from pipeline_eval import norm_name, score_report  # noqa: E402
from services.normalizer_service import normalize_report  # noqa: E402
from services.rule_engine import analyze_report  # noqa: E402
from services.vision_service import extract_with_ai  # noqa: E402


LEVELS = {
    # a mediocre phone photo: ~86 dpi, up to 3 degrees of tilt, JPEG quality 40-55
    "mild": (1.2, [40, 48, 55]),
    # a stress test: ~45 dpi, JPEG quality 22-40 (the text is a few pixels tall; hard even for a person)
    "harsh": (0.62, [22, 30, 40]),
}


def degrade(pdf_path, out_path, seed, level):
    """Make the scan look like a phone photo: lower resolution, slightly rotated, JPEG compression."""

    import pymupdf

    rng = random.Random(seed)
    source = pymupdf.open(str(pdf_path))
    result = pymupdf.open()
    angle = rng.uniform(-3, 3)
    scale, qualities = LEVELS[level]

    for page in source:
        matrix = pymupdf.Matrix(scale, scale).prerotate(angle)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        jpeg = pixmap.tobytes("jpeg", jpg_quality=rng.choice(qualities))
        new_page = result.new_page(width=pixmap.width, height=pixmap.height)
        new_page.insert_image(new_page.rect, stream=jpeg)

    result.save(str(out_path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--degrade", choices=list(LEVELS), help="simulate a phone photo of this quality")
    ap.add_argument("--dirs", nargs="+", default=[str(HERE / d) for d in ("synthetic", "synthetic_holdout", "synthetic_v2")])
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    keys = []
    for d in args.dirs:
        for p in sorted(Path(d).glob("report_*.json")):
            key = json.loads(p.read_text(encoding="utf-8"))
            if not key["expect_readable"]:
                keys.append((Path(d), key))

    random.Random(args.seed).shuffle(keys)

    totals, errors, perfect = Counter(), 0, 0
    for directory, key in keys[: args.n]:
        source = directory / key["file"]
        if args.degrade:
            source = HERE / "results" / "_degraded.pdf"
            degrade(directory / key["file"], source, key["file"], args.degrade)

        try:
            rows, sex = extract_with_ai(source)
        except Exception as error:                          # quota / outage: not a scoring failure
            errors += 1
            print(f"ERROR  {key['file']}: {str(error)[:90]}", flush=True)
            time.sleep(4)
            continue

        findings = analyze_report(normalize_report(rows, sex))
        results, extras = score_report(key, findings, {norm_name(r["parameter"]) for r in rows})

        tests = len(results)
        found = sum(r["finding"] is not None for r in results)
        right = sum(not r["problems"] for r in results)
        status_ok = sum(bool(r["finding"]) and "wrong_status" not in r["problems"] for r in results)
        totals.update(tests=tests, found=found, right=right, status_ok=status_ok, extras=len(extras))
        perfect += right == tests and not extras

        bad = [f"{r['test']['printed_name']}:{','.join(r['problems'])}" for r in results if r["problems"]][:3]
        print(f"{'PASS' if right == tests and not extras else 'DIFF':<6}{key['file']:<36}{right}/{tests} right, "
              f"{len(extras)} extra  {'; '.join(bad)}", flush=True)
        time.sleep(4)                                       # stay under the free-tier request rate

    scored = len(keys[: args.n]) - errors
    if totals["tests"]:
        print(f"\n{scored} scanned reports read: tests found {totals['found']}/{totals['tests']} "
              f"({totals['found'] / totals['tests']:.0%}), fully correct {totals['right']}/{totals['tests']} "
              f"({totals['right'] / totals['tests']:.0%}), status right {totals['status_ok'] / totals['tests']:.0%}, "
              f"extras {totals['extras']}, perfect reports {perfect}/{scored}; {errors} API errors (not counted)")
    (HERE / "results" / "_degraded.pdf").unlink(missing_ok=True)
    (HERE / "results" / (f"scan_{args.degrade}.json" if args.degrade else "scan.json")).write_text(json.dumps(dict(totals, errors=errors, reports=scored, perfect=perfect), indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
