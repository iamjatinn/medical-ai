# Deploying AuraHealth (free database + small server + free frontend)

```
Browser ──► Vercel (React frontend, static)
               │  HTTPS, Authorization: Bearer <token>
               ▼
        Render (FastAPI in Docker) ──► Gemini API
               │
               ▼
        Neon (PostgreSQL: users, reports, findings, chats)
```

You need accounts at three services (all have a free tier for the database and frontend):
[Neon](https://neon.tech), [Render](https://render.com), [Vercel](https://vercel.com), plus your Google AI Studio API key.

> **Before you start:** this app handles health data. For a public demo, use sample reports only and keep the
> "educational, not medical advice" notice visible. Real patient data needs consent, privacy policy and
> security review (DPDP / GDPR / HIPAA depending on where users live).

## 1. Database (Neon)
1. Create a project and copy the **connection string** (it looks like `postgresql://user:pass@ep-xxxx.neon.tech/neondb?sslmode=require`).
2. Nothing else: the backend creates the tables on first start. The app accepts the URL exactly as Neon gives it.

## 2. Backend (Render)
1. Push this repository to GitHub (the `render.yaml` Blueprint is in the root).
2. Render dashboard → **New → Blueprint** → choose the repository. It builds `backend/Dockerfile.prod`.
3. When asked, fill in the secrets:
   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the Neon connection string |
   | `GEMINI_API_KEY` | your Google AI Studio key |
   | `CORS_ORIGINS` | your Vercel URL (add it after step 3; you can edit it later) |
   | `JWT_SECRET` | generated for you |
4. Wait for the deploy, then open `https://<your-service>.onrender.com/` → `{"message":"Medical AI Backend Running"}` and `/docs` for the API.

**Memory and cost:** the production image uses `fastembed` (ONNX) instead of PyTorch and measured about 290 MB of RAM, so it is set to Render's **free** plan (512 MB). The free plan sleeps after ~15 minutes without traffic, so the first request after a pause takes 30-60 s, and the first start is slow because the search index is built then. For an always-on demo switch `plan: free` to `starter` in `render.yaml`. If the free plan runs out of memory, Hugging Face Spaces (Docker) is the free fallback.

## 3. Frontend (Vercel)
1. **Add New → Project** → the repository → set **Root Directory** to `frontend`.
2. Environment variable: `VITE_API_URL` = `https://<your-service>.onrender.com` (no trailing slash).
3. Deploy. `frontend/vercel.json` makes page refreshes work for routes like `/dashboard`.
4. Go back to Render and set `CORS_ORIGINS` to the Vercel URL, then redeploy the backend.

## 4. Check it works
1. Open the Vercel URL → create an account → upload `data/sample_reports/sample_medical_report.pdf`.
2. Open the app in a **private window**, create a second account, and confirm you cannot see the first account's report.
3. Ask the chat a question and check `tools_used` in the browser's network tab.

## 5. Security checklist
- [ ] `JWT_SECRET` is long and random, and is **not** in git (the app refuses to start in production otherwise).
- [ ] `backend/.env` is not committed (it is git-ignored). If a key ever leaks, revoke it and create a new one.
- [ ] `CORS_ORIGINS` lists only your frontend URL.
- [ ] The Neon password is not the development one from `docker-compose.yml`.
- [ ] Set a spending/quota limit on the Gemini key. The per-user upload and chat limits protect it, but they live in memory: with more than one server instance each keeps its own counters (use Redis then).
- [ ] Tokens are stored in the browser's `localStorage`; for a high-risk app move to `HttpOnly` cookies.

## Run the production image locally
```powershell
docker build -f backend/Dockerfile.prod -t medical-ai-api .
docker run --rm -p 8100:8000 --env-file backend/.env `
  -e JWT_SECRET=<48+ random characters> `
  -e DATABASE_URL=postgresql://user:pass@host/db `
  medical-ai-api
```

## Backups and upkeep
- Neon keeps point-in-time history on the free tier for a short period; export with `pg_dump` for anything important.
- Schema changes: the app adds missing columns on startup (`database.py`). For anything bigger, add Alembic migrations.
- Re-run `evals/retrieval_eval.py` and `evals/agent_eval.py` after changing prompts, tools, chunking or the model.
