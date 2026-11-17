# Medical AI – Lab Report Analyzer

Upload a text-based lab report (PDF) and get:

- every test checked against its reference range (rule-based, no AI guessing),
- a plain-language AI explanation grounded in a medical knowledge base (**RAG**),
- a chat assistant that answers follow-up questions about *your* report.

> ⚠️ Educational project. It is **not** a medical device and does not give diagnoses. Always consult a doctor.

**Stack:** FastAPI · PyMuPDF · Sentence-Transformers · FAISS · Google Gemini · React + Vite + Tailwind

---

## How it works

```
PDF ──► extract text (PyMuPDF)
    ──► parse rows (test, value, reference range, status)     parser_service
    ──► normalise numbers / units / ranges                    normalizer_service
    ──► rule engine: Low / Normal / High per test             rule_engine
    ──► RAG: embed a query per abnormal finding,
        search the FAISS index of medical documents           rag_service
    ──► Gemini writes the explanation from findings + chunks  ai_service
    ──► report saved as JSON, chat uses it as context         chat_service
```

**Why rules *and* AI?** Deciding whether 11.2 g/dL is below 13.5 is arithmetic, so it is done by code
(deterministic, testable). The LLM only *explains* the result, and it is given retrieved
knowledge instead of relying on memory.

### The RAG part

- Knowledge lives in `data/medical_docs/*.txt`: 53 MedlinePlus lab-test pages (U.S. National Library of Medicine, public domain, credited) plus 6 short project notes. See [data/SOURCES.md](data/SOURCES.md). Files are split into ~500-character chunks (50 overlap, cut at word boundaries).
- Chunks are embedded with `all-MiniLM-L6-v2` (384 dimensions, L2-normalised), so a FAISS inner-product index (`IndexFlatIP`) returns **cosine similarity**.
- Only chunks scoring ≥ `MIN_SIMILARITY` (0.45) are used, so an unrelated question retrieves nothing instead of the "least bad" chunk.
- The index is saved to `backend/vector_store/` and re-used on the next start. A SHA-256 fingerprint of the knowledge files, chunk settings and embedding model decides whether it must be rebuilt, so editing a `.txt` file is picked up automatically.
- Retrieval runs only for **abnormal** findings, plus once for the user's chat question.

---

## Run it

**Backend** (Python 3.10+)

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then put your GEMINI_API_KEY in .env
uvicorn main:app --reload     # http://127.0.0.1:8000/docs
```

The first start downloads the embedding model and builds the index (about 30 s); later starts load it in under a second.
Without an API key the app still runs – the AI text just says it is not configured.

**Frontend**

```powershell
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

**Tests** (no API key or model download needed)

```powershell
backend\venv\Scripts\python -m unittest discover -s tests -v
```

## Chat agent (tool use)

`/chat` is a small agent. Gemini can call four tools instead of guessing, and the code runs them and returns exact results:

| Tool | Used for |
|---|---|
| `get_report_findings` | "which results are abnormal?" |
| `get_parameter_details` | value, unit, range and status of one test |
| `compute_deviation` | exact "% below/above normal" (the model never does the arithmetic) |
| `search_knowledge` | general medical information from the FAISS knowledge base |

Design choices: the loop is written by hand (visible, limited to 5 steps); every tool is bound to one report, so the model can never read another report; tool errors are returned to the model instead of raised; if the agent fails, chat falls back to a single RAG prompt. The API returns `tools_used` for each answer.

## Evaluation

Run these after changing prompts, tools, chunking or the model.

```powershell
backend\venv\Scripts\python evals\retrieval_eval.py     # no API key needed
backend\venv\Scripts\python evals\agent_eval.py         # needs the stack running and Gemini quota
```

**Retrieval** (`evals/retrieval_eval.py`): 40 questions whose answer should be in the knowledge base (each with the acceptable source pages) plus 10 unrelated or uncovered questions that should return nothing, run against the real index (724 chunks from 59 documents).

| Similarity threshold | hit@1 | hit@3 | MRR | unrelated questions correctly rejected |
|---|---|---|---|---|
| 0.35 | 0.97 | 1.00 | 0.98 | 80 % |
| **0.45 (used)** | **0.97** | **1.00** | **0.98** | **80 %** |
| 0.50 | 0.95 | 0.95 | 0.95 | 100 % |
| 0.55 | 0.85 | 0.85 | 0.85 | 100 % |

Reading it honestly: with 59 documents, medical-sounding questions the knowledge base does not cover ("what causes high blood pressure", "symptoms of a heart attack") now score 0.47-0.49, just above the threshold, so 2 of 10 unrelated questions retrieve a loosely related passage. Raising the threshold to 0.50 rejects all of them but loses correct answers; 0.45 was kept because an irrelevant passage is mostly harmless (the model can ignore it) while a missed one loses information. The questions are hand-written by the author, so this is a regression guard, not a benchmark.

**Synthetic lab reports** (`evals/generate_reports.py`, `evals/pipeline_eval.py`): a seeded generator writes random PDFs (35 tests with name variants, units and per-sex ranges; 9 layouts including two-column, grouped tables, flag letters, no status column, and scanned images) together with an answer key. The real pipeline (PDF text, parser, normaliser, rule engine) is scored against the key, then the real embedding model checks that every truly abnormal test finds an explanation page. Nothing here calls the AI.

| Run | Parsing: tests found / fully correct | Status right | Scanned PDFs refused cleanly | Abnormal tests with a relevant page in top 3 |
|---|---|---|---|---|
| First run (seed 7, 138 text reports, 918 tests) | 73 % / - | - | 12 / 12 | - |
| After parser fixes, tuned on this seed | 100 % / 100 % | 100 % | 12 / 12 | - |
| **Fresh holdout (seed 2024, 189 text reports, 1,298 tests)** | **100 % / 100 %** | **100 %** | **11 / 11** | 95 % before, **100 %** after (168 tests) |

What the failures taught: a PDF font turned the en dash in `98 - 107` into a middle dot, so ranges were not parsed (parser now accepts dash variants, `to` and `~`); names that start with digits (`25-OH Vitamin D`); units containing digits on the range line (`mL/min/1.73m2 > 60`); a name and value on one line with the unit below; and a flag letter glued to the value (`27 L` then `U/L`, once read as unit `L U/L`). The first fix round was tuned on seed 7, so the fresh seed was the real test: it found three more misses (a flag after the value on a unit-and-range line, and a name-value-flag line), which were fixed and are now unit tests. The knowledge-coverage misses were all abbreviations (TG, HCT, HDL-C, FBS, PLT, Hb, PCV), fixed by spelling the abbreviation out in the search query. Limits: the generator and the parser were written by the same person, so 100 % means "handles every layout I thought of", not "handles every lab in the world"; real-world formats will still surprise it.

**Chat agent** (`evals/agent_eval.py`): 14 questions through the live API, scored by rules: the right tool was chosen, the answer contains the expected facts, it contains no invented number, no diagnosis or dosage, and off-topic or "ignore your instructions" requests are refused. API errors (quota, outage) are reported as `ERROR` and are never counted as failures. Results are written to `evals/results/agent_<label>.json`.

**Latest full run** (final stack: 59-document MedlinePlus knowledge base, default model chain, 14 questions, no API errors): **14 / 14 passed**. Exact calculations 2/2, knowledge retrieval 2/2, no invented values 1/1, off-topic and prompt-injection refusals 2/2, no diagnosis / no dosage 2/2, concise summary 1/1, tool choice and grounding 4/4. History, stated plainly: the first clean run scored 13/14; the one miss was a correct answer ("145 mg/dL, which is above the reference range") that my check rejected because it expected the word "high". I widened that check to accept "above" and "elevated", and the later full run passed every case. Because that check was changed after seeing a result, treat 13/14 as the unbiased figure and 14/14 as the current regression baseline. Rule-based checks on a small set are a regression guard, not proof of clinical safety.

## Gemini models and fallback

`GEMINI_MODELS` is an ordered list (default `gemini-3.1-flash-lite,gemini-3.6-flash,gemini-2.5-flash`). Every Gemini call (plain, structured output, tool-using chat) tries the first model and moves to the next on `503` (overloaded), `429` (quota), `404` (model retired) or a timeout (60 s). A bad request or a bad API key is raised immediately instead of being retried. `evals/compare_models.ps1` checks each model for structured output, tool calling and latency; `evals/results/model_smoke.json` has the latest run.

## Deploy

Frontend on Vercel, API in Docker on Render, PostgreSQL on Neon: step-by-step in [DEPLOY.md](DEPLOY.md) (`render.yaml` and `frontend/vercel.json` are included).

Two Docker images:

| | `backend/Dockerfile` (development) | `backend/Dockerfile.prod` |
|---|---|---|
| Embeddings | sentence-transformers (PyTorch) | **fastembed (ONNX), same model** |
| Image size | 2.76 GB | 1.3 GB |
| Memory while running | about 440 MB idle, over 1 GB under load | **about 290 MB** |
| User | root | non-root |
| `APP_ENV` | development | production (refuses to start without a strong `JWT_SECRET`) |

The two embedding backends return identical retrieval scores on the evaluation set (see `evals/results/retrieval.json` and `retrieval_fastembed.json`), so the lightweight one costs nothing in quality. Choose with `EMBEDDING_BACKEND=fastembed`.

## Accounts and privacy

Every report belongs to a user. Nothing is visible without logging in.

- **Passwords:** hashed with bcrypt (salted, slow on purpose). A wrong email and a wrong password return the same message, so accounts cannot be enumerated.
- **Login:** returns a signed JWT (12 h). Expired, tampered, foreign-signed and `alg: none` tokens are rejected.
- **Access control in the query:** every read, chat, list and delete runs `WHERE id = ... AND user_id = ...`. Someone else's report is indistinguishable from a missing one (`404`), so ids cannot be probed. Tests cover a second user trying to read, chat with, list and delete another user's report.
- **Rate limits:** failed logins, sign-ups per address, and uploads/messages per user (protects passwords and the AI quota). In-memory, per server process.
- **Delete your data:** `DELETE /reports/{id}` removes a report with its findings and chat.
- **Logout** removes the token and any report kept in the browser.
- **Production:** with `APP_ENV=production` the server refuses to start unless `JWT_SECRET` is set (32+ characters).

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/auth/register` | no | create an account, returns a token |
| `POST` | `/auth/login` | no | form login (`username` = email), returns a token |
| `GET`  | `/auth/me` | yes | the current user |
| `POST` | `/upload-report` | yes | multipart PDF → findings + structured analysis + `report_id` |
| `GET`  | `/reports` | yes | your reports, newest first |
| `GET`  | `/reports/{id}` | yes | one report with its chat history |
| `DELETE` | `/reports/{id}` | yes | delete a report and its chat |
| `POST` | `/chat` | yes | `{report_id, question}` → answer, `tools_used` |
| `GET`  | `/` | no | health check |

Send the token as `Authorization: Bearer <token>`. In the interactive docs (`/docs`) use the **Authorize** button.

Errors are explicit: `400` not a PDF, `401` not logged in, `404` unknown or not your report, `409` email already registered, `413` too large (limit 10 MB), `422` invalid input / no lab results / scanned PDF, `429` rate limit.

## Safety and robustness

- Uploads are saved under a random name, size-limited, checked for the `%PDF-` header, and **deleted after processing**.
- `report_id` must be a UUID, which blocks path-traversal ids.
- The Gemini client is created lazily; failures return a friendly message instead of a stack trace.
- Chat prompt refuses off-topic questions and never diagnoses or prescribes.

## Bugs found and how they were fixed

Every item below was a real failure found while building or testing, with what caused it and what changed. Most have a regression test, so they cannot come back silently.

### Found by the synthetic-report evaluation

| Symptom | Root cause | Fix (file) |
|---|---|---|
| Only 73 % of tests found on the first run | The PDF font turned the dash in `98 - 107` into a middle dot, so the range regex never matched | Added `RANGE_SEPARATORS` (hyphen, en/em dash, minus, middle dot, `~`, `to`) and used it in both the parser and the normaliser (`parser_service.py`, `normalizer_service.py`) |
| `25-OH Vitamin D` skipped | The test-name pattern had to start with a letter | Allow an optional leading `digits-` prefix in row and cell patterns (`parser_service.py`) |
| `eGFR` skipped | The unit `mL/min/1.73m2` contains digits and sat on the same line as the range (`mL/min/1.73m2 > 60`), which the cell layout did not expect | New `UNIT_RANGE_LINE_RE` handles a "unit + range" line |
| `WHITE BLOOD CELL COUNT 10.2` skipped | Name and value were on one line with the unit on the next | New `NAME_VALUE_RE` handles that layout |
| Unit read as `L U/L` and `L mL/min/1.73m2` | A flag letter glued to the value (`27 L`, then `U/L` on the next line) was treated as part of the unit | New `VALUE_FLAG_RE` splits the flag off the value and uses it as the status |
| Abnormal `TG`, `HCT`, `HDL-C`, `FBS`, `PLT`, `Hb`, `PCV` found no explanation page (coverage 95 %) | The knowledge pages use full names; the search query used the printed abbreviation | `expand_abbreviations` spells the abbreviation out in the query and keeps the original (`query_builder.py`). Coverage 100 % |

Lesson from this round: after tuning on one random seed the parser scored 100 %, but a fresh seed found three more misses. Always test on data you did not tune on.

### Found while building the app

| Symptom | Root cause | Fix |
|---|---|---|
| AI answers ignored the report | The `{report}` placeholder was missing from `REPORT_PROMPT` | Restored it and added a regression test (`test_prompt.py`) |
| The FAISS index was rebuilt on every start | `save()` wrote literal strings instead of the configured paths, so nothing persisted | Use the config paths; the index also stores a content fingerprint and rebuilds only when documents, backend or manifest change |
| Gemini error "JSON mode not enabled for api version v1" | The client used API version `v1`, which has no structured output | Client uses `v1beta`, with a regression test |
| Gemini 429 / 503 / 404 stopped the app | One model, no fallback | `GEMINI_MODELS` chain: 503, 429, 404 or a timeout moves to the next model; 400, 401 and 403 raise (real errors) (`gemini_service.py`) |
| API errors counted as failed agent answers in the eval | The eval treated any non-answer as a failure | Errors are reported as `ERROR` and excluded from the score |
| Chat said "fasting glucose" was not in the report | Exact-name lookup; the report listed "Glucose (Fasting)" | Fuzzy token matching plus an alias table (`tools_service.py`) |
| Aliases silently did nothing | A hidden backspace character (`\x08`) from an escape mistake turned `\b` into a control character in a regex | Replaced with lookarounds `(?<![a-z0-9])...(?![a-z0-9])`; checked the file for other control characters |
| `status_check` agent case failed on a correct answer ("above the reference range") | My check only accepted the word "high" | Widened to "above" / "elevated". README keeps the honest history: 13/14 unbiased, 14/14 baseline |
| An eval run overwrote the committed `retrieval.json` | Results are written to a fixed path | Restored from git; result files for runs you do not want to keep should not be committed |
| Docker "No such image" and `docker` not found | Build and `up` ran out of order; Docker's `bin` folder was missing from PATH in that shell | Build first, then `up`; refresh PATH |
| Passwords or weak secrets in production | A guessable `JWT_SECRET` would have been accepted | `APP_ENV=production` refuses to start with a weak secret; in dev an empty secret means a random per-start secret |

## Known limitations (honest list)

- **PDF layouts:** the parser understands "one test per line" and "one table cell per line" layouts. Reports with very different layouts, multi-column pages or scanned images (no OCR) are not supported yet and return a clear `422`.
- **Knowledge base is limited to lab-test pages** (53 MedlinePlus pages + 6 notes). Answers are only as good as these documents; conditions, drugs and non-lab topics are not covered, and a medical professional should review the content before any real use.
- Reports are stored as local JSON files; there is no authentication or database yet.
- Reference ranges come from the report itself and are not adjusted for age or sex.

## Roadmap

OCR for scanned reports · more knowledge documents and sources · database + authentication · streaming answers · deployment.

---

<details>
<summary>Development log</summary>

- **Day 1–2:** FastAPI setup, PDF upload endpoint, uploads directory.
- **Day 3:** PyMuPDF extraction, parser, normaliser, rule engine, Gemini summary, modular services.
- **Day 4:** validation, error handling, logging, Pydantic response models, prompt templates.
- **Day 5:** Sentence-Transformers embeddings, FAISS vector search, chunking, RAG connected to Gemini.
- **Day 6:** central config, persistent FAISS index, query builder.
- **Hardening pass:** fixed index persistence, restored the AI prompt's `{report}` placeholder, generic parser, one-sided ranges, upload/ID safety, cosine similarity with a relevance threshold, automatic index rebuild, test suite, frontend field mapping.

</details>
