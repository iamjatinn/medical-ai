"""Chat-agent evaluation against the RUNNING API (live Gemini).

For each question the script uploads the sample report (so every case starts
with a fresh, empty chat history), asks the question, and checks:

  tools     the assistant used a suitable tool (or none, for off-topic questions)
  contain   the answer includes the expected facts (case-insensitive)
  must_not  the answer does NOT contain forbidden things (a diagnosis, a dose,
            an invented number, an answer to an off-topic question)
  length    the answer is not longer than allowed

These are rule-based checks, so they are cheap, repeatable and easy to explain.
LLM output varies between runs, so treat the score as a measurement, not a
guarantee, and re-run it after changing prompts, tools or the model.

Start the stack first (docker compose up -d), then from the repo root:
    backend\\venv\\Scripts\\python evals\\agent_eval.py
"""

import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
API = os.getenv("API_URL", "http://localhost:8000")
SAMPLE = ROOT / "data" / "sample_reports" / "sample_medical_report.pdf"
PAUSE_SECONDS = float(os.getenv("EVAL_PAUSE", "8"))      # stay under API rate limits
RETRIES = 3
RETRY_WAIT = 45.0

API_ERROR_MARKERS = (
    "AI analysis could not be generated",
    "AI analysis is temporarily unavailable",
    "AI analysis is not configured",
)


def is_api_error(answer: str) -> bool:
    """The backend's friendly messages for when Gemini itself failed."""
    return any(marker in answer for marker in API_ERROR_MARKERS)


def upload_report(client):
    with open(SAMPLE, "rb") as file:
        response = client.post(f"{API}/upload-report", files={"file": (SAMPLE.name, file, "application/pdf")})
    response.raise_for_status()
    return response.json()["result"]["report_id"]


def check(case, answer, tools_used):
    """Return a list of reasons the case failed (empty list = pass)."""

    problems = []
    text = answer.lower()

    if case.get("no_tools") and tools_used:
        problems.append(f"should not call tools, but called {tools_used}")

    if case.get("tools_any") and not set(case["tools_any"]) & set(tools_used):
        problems.append(f"expected one of {case['tools_any']}, used {tools_used or 'none'}")

    for group in case.get("must_contain", []):
        if not any(option.lower() in text for option in group):
            problems.append(f"answer is missing any of {group}")

    for pattern in case.get("must_not_match", []):
        if re.search(pattern, answer):
            problems.append(f"answer matches forbidden pattern {pattern!r}")

    if case.get("max_chars") and len(answer) > case["max_chars"]:
        problems.append(f"answer is {len(answer)} chars (limit {case['max_chars']})")

    return problems


def main():

    cases = json.loads((HERE / "agent_cases.json").read_text(encoding="utf-8"))

    try:
        httpx.get(f"{API}/", timeout=5).raise_for_status()
    except Exception:
        sys.exit(f"The API is not reachable at {API}. Start it with: docker compose up -d")

    results = []

    with httpx.Client(timeout=180) as client:

        print(f"\nAgent eval  |  {len(cases)} questions  |  {API}\n")

        for case in cases:

            started = time.time()

            errored = False

            try:
                report_id = upload_report(client)

                # An API error (quota, outage) is NOT a quality failure: retry with
                # a pause, and if it keeps failing report the case as ERROR.
                for attempt in range(1, RETRIES + 1):
                    reply = client.post(f"{API}/chat", json={"report_id": report_id, "question": case["question"]})
                    reply.raise_for_status()
                    body = reply.json()
                    answer, tools_used = body["answer"], body.get("tools_used", [])

                    if not is_api_error(answer):
                        break

                    if attempt < RETRIES:
                        print(f"      (API error, waiting {RETRY_WAIT:.0f}s before retry {attempt + 1}/{RETRIES})")
                        time.sleep(RETRY_WAIT)

                errored = is_api_error(answer)
                problems = [] if errored else check(case, answer, tools_used)

            except Exception as error:
                answer, tools_used, problems, errored = "", [], [f"request failed: {error}"], True

            seconds = time.time() - started

            status = "ERROR" if errored else ("PASS" if not problems else "FAIL")

            results.append({**case, "answer": answer, "tools_used": tools_used, "problems": problems,
                            "status": status, "passed": status == "PASS", "seconds": round(seconds, 1)})

            print(f"{status:<6}{case['id']:<20} tools={tools_used or '-'}  ({seconds:.0f}s)")
            if errored:
                print("        - the AI service returned an error (quota/outage); not counted in the score")
            for problem in ([] if errored else problems):
                print(f"        - {problem}")

            time.sleep(PAUSE_SECONDS)

    by_category = defaultdict(lambda: [0, 0])

    scored = [r for r in results if r["status"] != "ERROR"]
    errors = len(results) - len(scored)

    for result in scored:
        by_category[result["category"]][1] += 1
        by_category[result["category"]][0] += result["passed"]

    passed = sum(r["passed"] for r in scored)

    print("\nBy category (scored cases only):")
    for category, (ok, total) in by_category.items():
        print(f"  {category:<28}{ok}/{total}")

    if scored:
        print(f"\nOverall: {passed}/{len(scored)} passed ({passed / len(scored):.0%})")
    if errors:
        print(f"{errors} case(s) hit AI-service errors and were NOT scored. "
              "Re-run later or set GEMINI_MODEL to another model.")

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "agent.json").write_text(json.dumps({
        "date": datetime.now().isoformat(timespec="seconds"),
        "passed": passed, "scored": len(scored), "errors": errors, "total": len(results),
        "by_category": {k: {"passed": v[0], "total": v[1]} for k, v in by_category.items()},
        "cases": results,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Saved evals/results/agent.json")


if __name__ == "__main__":
    main()
