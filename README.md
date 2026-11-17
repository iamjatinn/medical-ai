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

- Knowledge lives in `data/medical_docs/*.txt`. Files are split into ~500-character chunks (50 overlap, cut at word boundaries).
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

**Retrieval** (`evals/retrieval_eval.py`): 24 questions with a known source document, plus 11 unrelated or out-of-knowledge questions that should return nothing.

| Similarity threshold | hit@1 | hit@3 | MRR | unrelated questions correctly rejected |
|---|---|---|---|---|
| 0.25 | 1.00 | 1.00 | 1.00 | 82 % |
| 0.35 | 1.00 | 1.00 | 1.00 | 91 % (a blood-pressure question scored 0.37) |
| **0.45 (used)** | **1.00** | **1.00** | **1.00** | **100 %** |
| 0.55 | 0.71 | 0.71 | 0.71 | 100 % |

Caveats: the knowledge base is six short documents and the questions are hand-written, so this is a sanity check and not a production benchmark. One question passes by a thin margin (0.453 vs 0.45).

**Chat agent** (`evals/agent_eval.py`): 14 questions through the live API, scored by rules: the right tool was chosen, the answer contains the expected facts, it contains no invented number, no diagnosis or dosage, and off-topic or "ignore your instructions" requests are refused. API errors (quota, outage) are reported as `ERROR` and are never counted as failures. Results are written to `evals/results/agent.json`; no pass rate is published here until a full clean run completes.

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

## Known limitations (honest list)

- **PDF layouts:** the parser understands "one test per line" and "one table cell per line" layouts. Reports with very different layouts, multi-column pages or scanned images (no OCR) are not supported yet and return a clear `422`.
- **Knowledge base is small** (six short documents). The pipeline scales, but answers are only as good as the documents, which should be reviewed by a medical professional.
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
