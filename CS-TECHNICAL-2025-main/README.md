# AICareerStudio

A full‑stack employability assistant that helps candidates:
- Upload resumes securely (encrypted at rest) and extract structured data
- Get AI‑assisted resume reviews and a 6‑month career plan
- Practice AI interviews with live feedback via Socket.IO
- Discover relevant jobs and rank them by skills and region

This repo contains a Flask backend (API + Socket.IO) and a Next.js frontend (app router) wired together for local development.

## Tech Stack
- **Backend**: Flask, Flask‑CORS, Flask‑JWT‑Extended, Flask‑Limiter, Flask‑Talisman, Flask‑SocketIO, PyMongo, cryptography (Fernet), pypdf, requests
- **LLM**: OpenRouter/OpenAI client with JSON‑constrained prompts
- **Data**: MongoDB (Docker‑run locally)
- **Frontend**: Next.js 16 (App Router), React 19, Tailwind (v4), Socket.IO client, Axios

## Architecture
- Frontend (`frontend/`): Auth pages, dashboard, interview UI; calls backend REST/WebSocket.
- Backend (`backend/`):
  - Auth (`/auth/register`, `/auth/login`) with JWT
  - Upload + parsing → encrypts original file, stores plaintext JSON alongside, caches in memory
  - AI review/report endpoints and job matching
  - Interview session via Socket.IO with simple face‑metrics feedback loop
  - MongoDB stores users and resume metadata

## Run Locally
Below uses Windows PowerShell and Docker Desktop.

1) Start MongoDB via Docker
```powershell
docker pull mongo:7
docker volume create cs-mongo-data
docker run -d --name cs-mongo -p 27017:27017 -v cs-mongo-data:/data/db mongo:7
```

2) Backend (venv + requirements)
```powershell
Set-Location "c:\Users\darkloverr\Desktop\test2\backend"
python -m venv .venv 
.venv\Scripts\Activate
pip install -r requirements.txt
```

3) Backend env (`backend/.env`)
```
ENV=dev
APP_SECRET_KEY=dev-only-secret-change-me
JWT_SECRET_KEY=dev-only-jwt-secret-change-me
FERNET_KEY=<32-byte-base64-fernet-key>
MONGO_URI=mongodb://localhost:27017
MONGO_DB=cs_chall
CORS_ORIGINS=http://localhost:3000
# Optional admin seed
# ADMIN_EMAIL=admin@example.com
# ADMIN_PASSWORD=ChangeMe123
# One of the following for LLM features
# OPENROUTER_API_KEY=...
# OPENAI_API_KEY=...
```

4) Start backend
```powershell
python app.py
# -> http://localhost:8000
```

5) Frontend
```powershell
Set-Location "c:\Users\darkloverr\Desktop\test2\frontend"
npm install
npm run dev
# -> http://localhost:3000
```

Optional `frontend/.env.example`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## What’s Done
- Secure upload with Fernet encryption at rest
- Resume parsing: text extraction + heuristics (skills, roles, education, experience, region)
- AI: resume review, 6‑month plan, resume tailoring, cover letter
- Auth: JWT, per‑route rate limits, CORS
- Jobs: multi‑source scraping + curated fallbacks, region/mode filtering
- Interview: questions, scoring heuristic, face‑attention nudges, Socket.IO events

## Next Steps (Ideas)
- Persist interview sessions and analyses to Mongo with user timeline
- Add pagination and richer filters to job results
- Expand tests and add CI workflow

## More Docs
- Backend details: `backend/README.md`
- Frontend details: `frontend/README.md`
