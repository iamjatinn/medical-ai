"""Retrieval evaluation: does the FAISS search find a relevant document?

Every in-scope question lists which documents are acceptable answers (a topic
such as "anemia" accepts several related documents, because a hemoglobin or
iron question is legitimately answered by more than one page). We measure:

  hit@1   the top result is an acceptable document
  hit@3   an acceptable document is somewhere in the top 3
  MRR     mean reciprocal rank (1 for rank 1, 1/2 for rank 2, ...)
  abstain for unrelated questions the search should return NOTHING
          (this is what MIN_SIMILARITY is for)

It also sweeps the similarity threshold to show the trade-off between "finds
the answer" and "stays quiet when the question is unrelated".

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

from config import EMBEDDING_BACKEND, MIN_SIMILARITY, TOP_K  # noqa: E402
from services.index_builder import build_index  # noqa: E402

THRESHOLDS = [0.0, 0.25, 0.35, 0.40, 0.45, 0.50, 0.55, 0.65]


def main():

    cases = json.loads((HERE / "retrieval_cases.json").read_text(encoding="utf-8"))
    topics = cases["topics"]

    rag = build_index()

    print(f"\nIndex: {len(rag.documents)} chunks from "
          f"{len({s.get('name') for s in rag.sources})} documents")

    def search(query):
        # one search with no threshold; thresholds are applied afterwards
        return [(r["source"].get("name", "?"), round(r["score"], 3))
                for r in rag.search(query, k=TOP_K, min_score=0.0)]

    in_scope = []
    for case in cases["in_scope"]:
        expected = case.get("expected") or topics[case["topic"]]
        in_scope.append({"query": case["query"], "expected": expected, "retrieved": search(case["query"])})

    out_of_scope = [{"query": q, "retrieved": search(q)} for q in cases["out_of_scope"]]

    def metrics(threshold):
        hit1 = hit3 = rr = 0.0

        for case in in_scope:
            kept = [name for name, score in case["retrieved"] if score >= threshold]

            if kept[:1] and kept[0] in case["expected"]:
                hit1 += 1

            ranks = [i for i, name in enumerate(kept) if name in case["expected"]]
            if ranks:
                hit3 += 1
                rr += 1 / (ranks[0] + 1)

        n = len(in_scope)
        abstained = sum(1 for c in out_of_scope if not any(s >= threshold for _, s in c["retrieved"]))

        return {"hit@1": hit1 / n, "hit@3": hit3 / n, "mrr": rr / n,
                "abstain_rate": abstained / len(out_of_scope)}

    chosen = metrics(MIN_SIMILARITY)

    print(f"\nRetrieval eval [{EMBEDDING_BACKEND}]  |  {len(in_scope)} in-scope + {len(out_of_scope)} out-of-scope"
          f"  |  top-k={TOP_K}  threshold={MIN_SIMILARITY}\n")

    print("In-scope questions (threshold applied):")
    for case in in_scope:
        kept = [(n, s) for n, s in case["retrieved"] if s >= MIN_SIMILARITY]
        if kept[:1] and kept[0][0] in case["expected"]:
            mark = "✓"
        elif any(n in case["expected"] for n, _ in kept):
            mark = "~"
        else:
            mark = "✗"
        top = ", ".join(f"{n.replace('mplus_', '')} {s:.2f}" for n, s in kept[:2]) or "(nothing above threshold)"
        print(f"{mark} {case['query'][:56]:<58}{top}")

    print("\nOut-of-scope questions (should return nothing):")
    for case in out_of_scope:
        kept = [(n, s) for n, s in case["retrieved"] if s >= MIN_SIMILARITY]
        best = max((s for _, s in case["retrieved"]), default=0)
        extra = "" if not kept else "  -> " + ", ".join(f"{n.replace('mplus_', '')} {s:.2f}" for n, s in kept[:2])
        print(f"{'✓' if not kept else '✗'} {case['query']:<58}best {best:.2f}{extra}")

    print("\nThreshold sweep:")
    print(f"{'threshold':<11}{'hit@1':<9}{'hit@3':<9}{'MRR':<9}{'abstain on unrelated'}")
    for t in THRESHOLDS:
        m = metrics(t)
        marker = "  <-- used" if t == MIN_SIMILARITY else ""
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
        "chunks": len(rag.documents),
        "documents": len({s.get("name") for s in rag.sources}),
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
