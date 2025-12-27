# Backend (Flask API + Socket.IO)

This service powers authentication, secure resume uploads and parsing, AI reviews/reports, interview sessions, and job matching. It uses MongoDB for users and resume metadata, Fernet for at‑rest encryption, and exposes Socket.IO for live interview feedback.

## Requirements
- Python 3.10+
- Docker Desktop (to run MongoDB locally)

## Setup
```powershell
# from repo root
Set-Location "c:\Users\darkloverr\Desktop\test2\backend"
python -m venv .venv ; . .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` (same dir as `app.py`):
```
ENV=dev
APP_SECRET_KEY=dev-only-secret-change-me
JWT_SECRET_KEY=dev-only-jwt-secret-change-me
FERNET_KEY=<32-byte-base64-fernet-key>
MONGO_URI=mongodb://localhost:27017
MONGO_DB=cs_chall
CORS_ORIGINS=http://localhost:3000
# Optional admin seeding
# ADMIN_EMAIL=admin@example.com
# ADMIN_PASSWORD=ChangeMe123
# LLM API key (one of)
# OPENROUTER_API_KEY=...
# OPENAI_API_KEY=...
```
Run MongoDB in Docker (PowerShell):
```powershell
docker pull mongo:7 ; docker volume create cs-mongo-data
docker run -d --name cs-mongo -p 27017:27017 -v cs-mongo-data:/data/db mongo:7
```

Start the API:
```powershell
python app.py
# -> http://localhost:8000
```

## Auth Flow
- POST `/auth/register` → creates user, returns short‑lived JWT
- POST `/auth/login` → returns short‑lived JWT
- Include `Authorization: Bearer <token>` for protected routes

## Key Endpoints
- POST `/upload` (JWT): upload PDF/TXT/DOC/DOCX
  - Encrypts original bytes to `uploads/<id>_<safe>.enc`
  - Saves parsed JSON to `uploads/<id>.json` and in‑memory cache
- GET `/resume/<id>` (JWT): fetch parsed payload
- DELETE `/resume/<id>` (JWT): remove in‑memory and on‑disk artifacts
- POST `/review/<id>` (JWT): LLM resume review; cached to `uploads/<id>_review.json`
- POST `/report/<id>` (JWT): LLM career report; cached to `uploads/<id>_analysis.json`
- POST `/match/<id>` (JWT): jobs ranked with options `{ region, countries[], work_mode, skills_override[] }`
- POST `/match/auto/<id>` (JWT): jobs ranked from parsed resume
- POST `/footprint/<id>` (JWT): GitHub/StackOverflow footprint snapshot
- Socket.IO: `join_interview`, `question`, `answer_done`, `face_metrics`, `feedback`, `final`

## Files and Logic
- `app.py` — Flask app wiring, CORS/Talisman, JWT + rate limits, Socket.IO events, routes for upload/review/report/match/footprint, encrypted storage, caching.
- `config.py` — `DevConfig`/`ProdConfig`, CORS defaults, size limits, prod secret validation.
- `auth.py` — Blueprint with `/auth/register`, `/auth/login`; CORS per‑route; limiter; seeds admin from env via `init_auth`.
- `auth_store.py` — Mongo connection (`MONGO_URI`, `MONGO_DB`), user CRUD with PBKDF2‑SHA256, resume metadata persistence, indexes.
- `storage.py` — In‑memory stores for files/resumes/sessions and `new_id()` helper.
- `parsers.py` — Resume text extraction (pypdf fallback), section heuristics, skills canonicalization, region inference (EMEA/AMER/APAC/Remote), experience/education parsing.
- `reviewer.py` — Heuristic ATS score/readability, gap detection, suggested summary/bullets.
- `llm_client.py` — OpenRouter/OpenAI chat calls for: structured analysis (career report), resume review, resume tailoring, cover letter. Ensures pure‑JSON outputs; trims code fences.
- `interviewer.py` — Base questions and simple answer scoring heuristic (keywords/STAR hints).
- `interview_insights.py` — Aggregates transcripts + face metrics into strengths/weaknesses and an overall score.
- `metrics.py` — Rolling EMA attention/smiles/presence with per‑question summaries and nudges.
- `helpers.py` — `_now`, `_ema` utilities.
- `footprint.py` — GitHub + StackOverflow API snapshots (top langs/tags, recent activity).
- `matcher.py` — Aggregates jobs, normalizes modes/regions, filters (MENA/SSA/countries, remote/onsite), scores via Jaccard + bonuses, curated fallbacks.
- `sources/noauth_jobs.py` — RemoteOK, Remotive, Arbeitnow, WWR scrapers (no auth); de‑dupe; basic skill matching.

## Development Notes
- Port: `8000` (set by `socketio.run` in `app.py`)
- CORS: defaults to `http://localhost:3000` (override `CORS_ORIGINS`)
- Secrets: in dev, defaults exist; in prod (`ENV=prod`) secrets are required
- Encryption: Fernet key must be set to accept uploads
