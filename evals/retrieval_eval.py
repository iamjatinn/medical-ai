"""Retrieval evaluation: does the FAISS search find the right document?

For every question we know which knowledge file *should* answer it. We measure:

  hit@1   the right document is the top result
  hit@3   the right document is somewhere in the top 3
  MRR     mean reciprocal rank (1 for rank 1, 1/2 for rank 2, ...)
  abstain for unrelated questions, the search should return NOTHING
          (this is what MIN_SIMILARITY is for)

It also sweeps the similarity threshold to show why the chosen value is a
good trade-off between "finds the answer" and "stays quiet when unrelated".

Run from the repo root (uses the real embedding model, no API key needed):
    backend\\venv\\Scripts\\python evals\\retrieval_eval.py
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))

logging.disable(logging.CRITICAL)

from config import EMBEDDING_BACKEND, KNOWLEDGE_FOLDER, MIN_SIMILARITY, TOP_K  # noqa: E402
from services.index_builder import build_index  # noqa: E402

THRESHOLDS = [0.0, 0.25, 0.35, 0.45, 0.55, 0.65]


def main():

    cases = json.loads((HERE / "retrieval_cases.json").read_text(encoding="utf-8"))

    docs = {p.stem: p.read_text(encoding="utf-8") for p in sorted(Path(KNOWLEDGE_FOLDER).glob("*.txt"))}

    def source_of(chunk):
        return next((name for name, text in docs.items() if chunk.strip() in text), "?")

    rag = build_index()

    # Search once with no threshold; apply thresholds afterwards.
    in_scope = []
    for case in cases["in_scope"]:
        results = rag.search(case["query"], k=TOP_K, min_score=0.0)
        in_scope.append({
            **case,
            "retrieved": [(source_of(r["text"]), round(r["score"], 3)) for r in results],
        })

    out_of_scope = []
    for query in cases["out_of_scope"]:
        results = rag.search(query, k=TOP_K, min_score=0.0)
        out_of_scope.append({
            "query": query,
            "retrieved": [(source_of(r["text"]), round(r["score"], 3)) for r in results],
        })

    def metrics(threshold):
        hit1 = hit3 = rr = 0.0

        for case in in_scope:
            kept = [src for src, score in case["retrieved"] if score >= threshold]
            if kept[:1] == [case["expected_source"]]:
                hit1 += 1
            if case["expected_source"] in kept:
                hit3 += 1
                rr += 1 / (kept.index(case["expected_source"]) + 1)

        n = len(in_scope)

        abstained = sum(
            1 for case in out_of_scope if not any(score >= threshold for _, score in case["retrieved"])
        )

        return {
            "hit@1": hit1 / n, "hit@3": hit3 / n, "mrr": rr / n,
            "abstain_rate": abstained / len(out_of_scope),
        }

    chosen = metrics(MIN_SIMILARITY)

    print(f"\nRetrieval eval [{EMBEDDING_BACKEND}]  |  {len(in_scope)} in-scope + {len(out_of_scope)} out-of-scope questions"
          f"  |  top-k={TOP_K}  threshold={MIN_SIMILARITY}\n")

    print("In-scope questions (threshold applied):")
    print(f"{'':2}{'question':<55}{'expected':<11}{'got (source, score)'}")

    for case in in_scope:
        kept = [(s, sc) for s, sc in case["retrieved"] if sc >= MIN_SIMILARITY]
        ok = "✓" if kept[:1] and kept[0][0] == case["expected_source"] else ("~" if any(s == case["expected_source"] for s, _ in kept) else "✗")
        print(f"{ok:<2}{case['query'][:53]:<55}{case['expected_source']:<11}{kept[:3]}")

    print("\nOut-of-scope questions (should return nothing):")
    for case in out_of_scope:
        kept = [(s, sc) for s, sc in case["retrieved"] if sc >= MIN_SIMILARITY]
        best = max((sc for _, sc in case["retrieved"]), default=0)
        print(f"{'✓' if not kept else '✗':<2}{case['query']:<55}best score {best:.2f}  returned {len(kept)}")

    print("\nThreshold sweep:")
    print(f"{'threshold':<11}{'hit@1':<9}{'hit@3':<9}{'MRR':<9}{'abstain on unrelated'}")
    for t in THRESHOLDS:
        m = metrics(t)
        marker = "  <-- chosen" if t == MIN_SIMILARITY else ""
        print(f"{t:<11}{m['hit@1']:<9.2f}{m['hit@3']:<9.2f}{m['mrr']:<9.2f}{m['abstain_rate']:.2f}{marker}")

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    file_name = (
        "retrieval.json" if EMBEDDING_BACKEND == "sentence-transformers"
        else f"retrieval_{EMBEDDING_BACKEND}.json"
    )

    (out_dir / file_name).write_text(json.dumps({
        "embedding_backend": EMBEDDING_BACKEND,
        "date": datetime.now().isoformat(timespec="seconds"),
        "top_k": TOP_K, "threshold": MIN_SIMILARITY,
        "questions": len(in_scope) + len(out_of_scope),
        "chosen_threshold_metrics": chosen,
        "sweep": {str(t): metrics(t) for t in THRESHOLDS},
        "in_scope": in_scope, "out_of_scope": out_of_scope,
    }, indent=2), encoding="utf-8")

    print(f"\nSummary @ threshold {MIN_SIMILARITY}: hit@1 {chosen['hit@1']:.0%}  hit@3 {chosen['hit@3']:.0%}  "
          f"MRR {chosen['mrr']:.2f}  abstain {chosen['abstain_rate']:.0%}")
    print(f"Saved evals/results/{file_name}")


if __name__ == "__main__":
    main()
