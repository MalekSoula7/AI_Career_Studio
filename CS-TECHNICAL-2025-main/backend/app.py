# app.py
from __future__ import annotations
import os, time, mimetypes, secrets, json
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit, join_room
from flask_talisman import Talisman
from werkzeug.utils import secure_filename

from cryptography.fernet import Fernet
from flask_jwt_extended import (
    JWTManager, jwt_required, verify_jwt_in_request, get_jwt
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# --- Load env BEFORE importing config (so config sees env) ---
ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(ENV_PATH)

# --- Local modules ---
from helpers import _now, _ema
from config import DevConfig, ProdConfig, validate_required_secrets

from interviewer import generate_questions, score_answer
from interview_insights import generate_insights
from metrics import _ensure_face_state, _finalize_face_summary, _reset_per_question_face_state

from storage import DB, new_id
from parsers import parse_resume_bytes
from reviewer import reviewer
from matcher import rank_jobs
from footprint import scan as footprint_scan
from llm_client import (
    analyze_resume_with_llm,
    analyze_resume_review_llm,
    refine_resume_for_job_llm,
    generate_cover_letter_llm,
)

# Auth blueprint (Mongo store lives in auth_store.py)
from auth import auth_bp, init_auth
from auth_store import save_resume  # <- persist resume metadata to Mongo

# ------------------------------
# App / Config
# ------------------------------
app = Flask(__name__)
app.config.from_object(ProdConfig if os.getenv("ENV") == "prod" else DevConfig)
validate_required_secrets()  # raises only when ENV=prod and secrets missing

# JWT + Limiter (limiter for non-auth routes; auth routes init inside init_auth)
jwt = JWTManager(app)
limiter = Limiter(key_func=get_remote_address, app=app, default_limits=["200 per hour"])

from flask_cors import CORS
cors_origins = os.getenv("CORS_ORIGINS", "*")

CORS(
    app,
    resources={r"/*": {"origins": cors_origins}},
    supports_credentials=False,
    allow_headers=["Authorization", "Content-Type"],
    methods=["GET", "POST", "DELETE", "OPTIONS", "PUT", "PATCH"],
)

# Security headers / CSP
if app.config.get("DEBUG"):
    # Dev: do not force HTTPS, allow localhost connects
    Talisman(
        app,
        force_https=False,
        content_security_policy={
            "default-src": ["'self'"],
            "img-src": ["'self'", "data:"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "script-src": ["'self'"],
            "connect-src": ["'self'", "http://localhost:8000", "ws://localhost:8000"],
            "media-src": ["'self'", "blob:"],
            "frame-ancestors": ["'none'"],
        },
        session_cookie_secure=False,
        session_cookie_samesite="Lax",
        frame_options="DENY",
        referrer_policy="strict-origin-when-cross-origin",
    )
else:
    # Prod: strict CSP + HTTPS
    Talisman(
        app,
        force_https=True,
        content_security_policy={
            "default-src": ["'self'"],
            "base-uri": ["'self'"],
            "img-src": ["'self'", "data:"],
            "style-src": ["'self'"],
            "script-src": ["'self'"],
            "connect-src": ["'self'", "https:", "wss:"],
            "media-src": ["'self'", "blob:"],
            "frame-ancestors": ["'none'"],
        },
        session_cookie_secure=True,
        session_cookie_samesite="Lax",
        frame_options="DENY",
        referrer_policy="strict-origin-when-cross-origin",
        permissions_policy={
            "camera": "()",
            "microphone": "()",
            "geolocation": "()",
            "fullscreen": "()",
        }
    )

# Auth blueprint (with its own per-route CORS and rate-limits)
app.register_blueprint(auth_bp, url_prefix="/auth")
init_auth(app)

# Fernet encryption
FERNET_KEY = os.getenv("FERNET_KEY")
fernet = Fernet(FERNET_KEY.encode()) if FERNET_KEY else None

# Upload settings
ALLOWED_EXTS = {"pdf", "txt", "doc", "docx"}
os.makedirs("./uploads", exist_ok=True)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTS



app.url_map.strict_slashes = False  # avoid /login -> /login/ redirects

IS_PROD = (os.getenv("ENV") == "prod") and not app.config.get("DEBUG", False)

# If you used Talisman, only force HTTPS in prod:
if IS_PROD:
    Talisman(app, force_https=True, content_security_policy={...})
else:
    Talisman(
        app,
        force_https=False,                 # <- important: no HTTPS redirect in dev
        content_security_policy={
            "default-src": ["'self'"],
            "img-src": ["'self'","data:"],
            "style-src": ["'self'","'unsafe-inline'"],
            "script-src": ["'self'"],
            "connect-src": ["'self'", "http://localhost:8000", "ws://localhost:8000"],
            "media-src": ["'self'","blob:"],
            "frame-ancestors": ["'none'"],
        },
        session_cookie_secure=False,
        session_cookie_samesite="Lax",
    )

# also make sure your .env has ENV=dev while developing




socketio = SocketIO(app, cors_allowed_origins="*")
ALLOWED_ORIGINS = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:8000", "http://127.0.0.1:8000",
]

@app.before_request
def _cors_preflight_shortcircuit():
    if request.method == "OPTIONS":
        origin = request.headers.get("Origin", "")
        resp = app.make_response(("", 204))
        if origin:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
        acrh = request.headers.get("Access-Control-Request-Headers", "Authorization, Content-Type")
        acrm = request.headers.get("Access-Control-Request-Method", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        resp.headers["Access-Control-Allow-Headers"] = acrh
        resp.headers["Access-Control-Allow-Methods"] = acrm
        resp.headers["Access-Control-Max-Age"] = "600"
        return resp

@socketio.on("connect")
def sio_connect(auth):
    """Dev: allow all Socket.IO connections without JWT for now."""
    print("[socket] client connected", auth)
    return True

# ------------------------------
# Frontend landing (optional)
# ------------------------------
@app.route("/")
def home():
    # If you serve a template, keep it; otherwise you can return a 200 JSON
    return render_template("index.html")

    
# ------------------------------
# Upload (Fernet at rest) – store raw text only
# ------------------------------
@limiter.limit("30/minute")
@app.route("/upload", methods=["POST"])
@jwt_required()
def upload():
    # Require encryption configured
    if not fernet:
        return jsonify({"error": "encryption unavailable: set FERNET_KEY"}), 500

    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "empty filename"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "extension not allowed"}), 400

    mime = f.mimetype or mimetypes.guess_type(f.filename)[0] or ""
    if not any(x in mime for x in ["pdf", "text", "officedocument", "msword"]):
        return jsonify({"error": "mime not allowed"}), 400

    raw_bytes = f.read()
    if not raw_bytes:
        return jsonify({"error": "empty file"}), 400

    # Encrypt and persist only ciphertext
    try:
        cipher = fernet.encrypt(raw_bytes)
    except Exception as e:
        return jsonify({"error": f"encryption failed: {e}"}), 500

    safe_name = secure_filename(f.filename)
    rid = secrets.token_hex(16)
    enc_path = f"./uploads/{rid}_{safe_name}.enc"

    try:
        with open(enc_path, "wb") as fh:
            fh.write(cipher)
    except Exception as e:
        return jsonify({"error": f"write failed: {e}"}), 500

    # Extract raw text from plaintext bytes (no further parsing here)
    try:
        parsed_for_text = parse_resume_bytes(raw_bytes)
        raw_text = parsed_for_text.get("raw_text", "")
        print(f"[upload] extracted raw_text length={len(raw_text)} for resume_id={rid}")
    finally:
        del raw_bytes  # minimize plaintext lifetime

    # Persist raw text JSON alongside encrypted blob
    json_path = f"./uploads/{rid}.json"
    payload = {
        "resume_id": rid,
        "raw_text": raw_text,
        "orig_name": safe_name,
        "mime": mime,
    }
    try:
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(payload, jf, ensure_ascii=False, indent=2)
    except Exception:
        # Non-fatal: continue even if JSON write fails
        pass

    # Cache minimal parsed in-memory for fast ops
    DB.setdefault("resumes", {})[rid] = payload
    DB.setdefault("files", {})[rid] = {
        "enc_path": enc_path,
        "orig_name": safe_name,
        "mime": mime,
        "size": len(cipher),
    }

    # Persist metadata to Mongo (user-scoped)
    try:
        claims = get_jwt()  # from @jwt_required()
        email = claims.get("email") or claims.get("sub")
        if email:
            save_resume(user_email=email, enc_path=enc_path, mime=mime, meta=payload)
    except Exception:
        # If Mongo fails, still return resume_id (you can log this)
        pass

    return jsonify({"resume_id": rid})

def load_encrypted_resume(enc_path: str) -> bytes:
    with open(enc_path, "rb") as fh:
        return fernet.decrypt(fh.read())

# ------------------------------
# Resume / Review
# ------------------------------
@app.get("/resume/<resume_id>")
@jwt_required()
def get_resume(resume_id: str):
    parsed = DB["resumes"].get(resume_id)
    if not parsed:
        return jsonify({"error": "Unknown resume_id"}), 404
    return jsonify(parsed)

@app.post("/review/<resume_id>")
@jwt_required()
def review(resume_id: str):
    payload = DB["resumes"].get(resume_id)
    if not payload:
        # Try to reload from disk if present
        json_path = f"./uploads/{resume_id}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    payload = json.load(jf)
                DB.setdefault("resumes", {})[resume_id] = payload
            except Exception:
                return jsonify({"error": "Resume could not be loaded from disk"}), 404
        else:
            return jsonify({"error": "Unknown resume_id"}), 404

    raw_text = payload.get("raw_text") or ""
    if not raw_text:
        return jsonify({"error": "No raw_text stored for this resume_id"}), 400

    # Check on-disk cache first
    cache_path = f"./uploads/{resume_id}_review.json"
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as fh:
                cached = json.load(fh)
            return jsonify(cached)
        except Exception:
            pass

    # LLM-based review per requested schema
    result = analyze_resume_review_llm(raw_text)

    try:
        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return jsonify(result)

# ------------------------------
# Interview (Socket + Insights)
# ------------------------------
@app.post("/interview/ai/start")
@jwt_required()
def interview_ai_start():
    data = request.get_json(force=True, silent=True) or {}
    resume_id = data.get("resume_id")
    role = data.get("role")
    if not resume_id or resume_id not in DB["resumes"]:
        return jsonify({"error": "Unknown resume_id"}), 404
    session_id = new_id()
    qs = generate_questions(DB["resumes"][resume_id], role)
    DB["sessions"][session_id] = {"resume_id": resume_id, "q": qs, "idx": 0, "scores": {}}
    return jsonify({"session_id": session_id, "first": qs[0] if qs else None})

@socketio.on("join_interview")
def on_join(data):
    session_id = (data or {}).get("session_id")
    if not session_id:
        emit("error", {"error": "missing session_id"}); return
    join_room(session_id)
    sess = DB["sessions"].get(session_id)
    if not sess:
        emit("error", {"error": "unknown session"}); return
    _finalize_face_summary(sess)  # initializes on first call
    q = sess["q"][sess["idx"]] if sess["q"] else None
    emit("question", {"question": q}, to=session_id)

SOCKET_LIMITS: Dict[str, Any] = {}

def allow_event(key: str, limit=10, per=5.0):
    now = time.time()
    bucket = SOCKET_LIMITS.get(key, {"tokens": limit, "updated": now})
    elapsed = now - bucket["updated"]
    bucket["tokens"] = min(limit, bucket["tokens"] + elapsed * (limit / per))
    bucket["updated"] = now
    SOCKET_LIMITS[key] = bucket
    if bucket["tokens"] >= 1:
        bucket["tokens"] -= 1
        return True
    return False

def drop_if_too_big(payload: dict, max_len=4096):
    if not isinstance(payload, dict): return False
    return sum(len(str(v)) for v in payload.values()) <= max_len

@socketio.on("transcript")
def on_transcript(data):
    session_id = (data or {}).get("session_id")
    text = ((data or {}).get("text") or "").strip()
    sess = DB["sessions"].get(session_id)
    if not sess:
        emit("error", {"error": "unknown session"}); return
    # lightweight realtime feedback
    feedback = None
    if any(x in text for x in ["%", "users", "latency", "revenue", "cost"]):
        feedback = "Great—keep quantifying impact."
    elif len(text.split()) > 30:
        feedback = "Nice depth; mention tools and metrics."
    emit("feedback", {"feedback": feedback}, to=session_id)

@socketio.on("answer_done")
def on_answer_done(data):
    session_id = (data or {}).get("session_id")
    answer = ((data or {}).get("answer") or "")
    sess = DB["sessions"].get(session_id)
    if not sess:
        emit("error", {"error": "unknown session"}); return

    qid = sess["q"][sess["idx"]]["id"]
    sess["scores"][qid] = score_answer(answer)
    sess.setdefault("answers", []).append(answer)
    sess["idx"] += 1
    _reset_per_question_face_state(sess)

    if sess["idx"] >= len(sess["q"]):
        face_summary = _finalize_face_summary(sess)
        insights = generate_insights(sess["scores"], sess.get("answers", []), face_summary)
        emit("final", {"done": True, "scores": sess["scores"], "face_summary": face_summary, "insights": insights}, to=session_id)
        return

    next_q = sess["q"][sess["idx"]]
    emit("question", {"question": next_q, "progress": f"{sess['idx']}/{len(sess['q'])}"}, to=session_id)

@socketio.on("face_metrics")
def on_face_metrics(data):
    session_id = (data or {}).get("session_id")
    if not session_id:
        emit("error", {"error": "missing session_id"}); return
    sess = DB["sessions"].get(session_id)
    if not sess:
        emit("error", {"error": "unknown session"}); return

    raw_attention = float(max(0.0, min(1.0, (data.get("attention") or 0.0))))
    smiling = bool(data.get("smiling") or False)
    faces = int(max(0, data.get("faces") or 0))

    st = _ensure_face_state(sess)
    st["ema_attention"] = _ema(st["ema_attention"], raw_attention, alpha=0.25)
    st["ema_faces"] = _ema(st["ema_faces"], float(faces), alpha=0.4)

    st["frames"] += 1
    if faces > 0: st["present_frames"] += 1
    if smiling:   st["smile_frames"] += 1

    now_ts = _now()
    ATTENTION_LOW, INATTENTIVE_SECS = 0.35, 8.0
    AWAY_FACES_NONE_SECS, NUDGE_COOLDOWN_SECS = 12.0, 20.0
    ema_att, ema_faces = st["ema_attention"] or 0.0, st["ema_faces"] or 0.0

    if ema_att < ATTENTION_LOW and faces > 0:
        if st["inattentive_since"] is None: st["inattentive_since"] = now_ts
    else:
        st["inattentive_since"] = None

    if faces == 0:
        if st["away_since"] is None: st["away_since"] = now_ts
    else:
        st["away_since"] = None

    last_nudge_ts = st.get("last_nudge_ts")
    can_nudge = (last_nudge_ts is None) or ((now_ts - last_nudge_ts) >= NUDGE_COOLDOWN_SECS)

    if st["inattentive_since"] and (now_ts - st["inattentive_since"] >= INATTENTIVE_SECS) and can_nudge:
        emit("feedback", {"feedback": "Tip: Keep eyes on the screen—helps with clarity and presence."}, to=session_id)
        st["nudges"] += 1; st["nudged_this_question"] = True; st["last_nudge_ts"] = now_ts

    if st["away_since"] and (now_ts - st["away_since"] >= AWAY_FACES_NONE_SECS) and can_nudge:
        emit("feedback", {"feedback": "We lost the face for a bit—recenter the camera when ready."}, to=session_id)
        st["nudges"] += 1; st["nudged_this_question"] = True; st["last_nudge_ts"] = now_ts

    if ema_att >= 0.75 and smiling and (st["frames"] % 90 == 0):
        emit("feedback", {"feedback": "Great presence 👍 Keep it up."}, to=session_id)

    last_emit = st.get("last_emit_ts") or 0
    if now_ts - last_emit >= 1.0:
        st["last_emit_ts"] = now_ts
        emit("face_status", {
            "ema_attention": round(ema_att, 3),
            "ema_faces": round(ema_faces, 3),
            "frames": st["frames"],
            "present_ratio": round(st["present_frames"] / max(1, st["frames"]), 3),
            "smile_ratio": round(st["smile_frames"] / max(1, st["frames"]), 3),
        }, to=session_id)

# ------------------------------
# Jobs / Match
# ------------------------------
@app.post("/match/<resume_id>")
@jwt_required()
def match(resume_id: str):
    data = request.get_json(force=True, silent=True) or {}
    print(f"[MATCH API] Received payload: {data}")
    region = data.get("region")
    skills_override = data.get("skills_override")
    countries = data.get("countries") or []
    work_mode = (data.get("work_mode") or "any").lower()
    if work_mode == "hybrid":
        work_mode = "any"

    parsed = DB["resumes"].get(resume_id)
    if not parsed:
        # Try to reload from disk if present
        json_path = f"./uploads/{resume_id}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    parsed = json.load(jf)
                DB.setdefault("resumes", {})[resume_id] = parsed
            except Exception:
                return jsonify({"error": "Resume could not be loaded from disk"}), 404
        else:
            return jsonify({"error": "Unknown resume_id"}), 404

    skills = (skills_override or parsed.get("skills", {}).get("hard", [])) or ["python"]
    jobs = rank_jobs(skills, region, roles=None, countries=countries, mode=work_mode)
    return jsonify({
        "region": region,
        "skills_used": skills,
        "countries": countries,
        "work_mode": work_mode,
        "jobs": jobs
    })

@app.get("/debug/scrape/<resume_id>")
def debug_scrape(resume_id: str):
    parsed = DB["resumes"].get(resume_id)
    if not parsed: return jsonify({"error":"Unknown resume_id"}), 404
    skills = parsed.get("skills",{}).get("hard",[]) or ["python","react","fastapi"]
    from sources.noauth_jobs import remoteok, remotive, arbeitnow, weworkremotely
    out = {
        "skills_used": skills[:12],
        "remoteok": len(remoteok(skills)),
        "remotive": len(remotive(skills)),
        "arbeitnow": len(arbeitnow(skills, pages=1)),
        "weworkremotely": len(weworkremotely(skills, max_pages=1)),
    }
    return jsonify(out)

@app.post("/match/auto/<resume_id>")
@jwt_required()
def match_auto(resume_id: str):
    parsed = DB["resumes"].get(resume_id)
    if not parsed:
        return jsonify({"error": "Unknown resume_id"}), 404
    from matcher import rank_from_resume
    jobs = rank_from_resume(parsed)
    return jsonify({
        "region": parsed.get("region"),
        "roles": parsed.get("roles"),
        "skills_used": parsed.get("skills", {}).get("hard", []),
        "jobs": jobs
    })

# ------------------------------
# Footprint
# ------------------------------
@app.post("/footprint/<resume_id>")
@jwt_required()
def footprint(resume_id: str):
    data = request.get_json(force=True, silent=True) or {}
    parsed = DB["resumes"].get(resume_id)
    if not parsed:
        return jsonify({"error": "Unknown resume_id"}), 404
    gh = data.get("github_username")
    so = data.get("stackoverflow_user_id")
    return jsonify(footprint_scan(gh, so))

# ------------------------------
# Career Insights Report
# ------------------------------
@app.post("/report/<resume_id>")
@jwt_required()
def report(resume_id: str):
    """Build a career report that combines resume review and a 6‑month plan.

    Today this is powered by a single LLM call on the raw resume text.
    Later we can thread in interview insights, footprint, or top job matches.
    """
    payload = DB["resumes"].get(resume_id)
    if not payload:
        # Try to reload from disk if present (mirror /review behavior)
        json_path = f"./uploads/{resume_id}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    payload = json.load(jf)
                DB.setdefault("resumes", {})[resume_id] = payload
            except Exception:
                return jsonify({"error": "Resume could not be loaded from disk"}), 404
        else:
            return jsonify({"error": "Unknown resume_id"}), 404

    raw_text = payload.get("raw_text") or ""
    if not raw_text:
        return jsonify({"error": "No raw_text stored for this resume_id"}), 400

    analysis_path = f"./uploads/{resume_id}_analysis.json"
    if os.path.exists(analysis_path):
        try:
            with open(analysis_path, "r", encoding="utf-8") as fh:
                cached = json.load(fh)
            return jsonify(cached)
        except Exception:
            pass

    analysis = analyze_resume_with_llm(raw_text)

    try:
        with open(analysis_path, "w", encoding="utf-8") as fh:
            json.dump(analysis, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return jsonify(analysis)

# ------------------------------
# Delete Resume (reset CV)
# ------------------------------
@app.delete("/resume/<resume_id>")
@jwt_required()
def delete_resume(resume_id: str):
    """Delete resume payload, encrypted file, and cached analyses.

    This lets the user reset their CV and upload a new one cleanly.
    """
    # Remove in-memory entries
    DB.get("resumes", {}).pop(resume_id, None)
    file_meta = DB.get("files", {}).pop(resume_id, None)

    # Remove JSON payload
    json_path = f"./uploads/{resume_id}.json"
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception:
            pass

    # Remove encrypted file if we have its path
    if file_meta and isinstance(file_meta, dict):
        enc_path = file_meta.get("enc_path")
        if enc_path and os.path.exists(enc_path):
            try:
                os.remove(enc_path)
            except Exception:
                pass

    # Remove cached review and analysis files if present
    review_path = f"./uploads/{resume_id}_review.json"
    if os.path.exists(review_path):
        try:
            os.remove(review_path)
        except Exception:
            pass

    analysis_path = f"./uploads/{resume_id}_analysis.json"
    if os.path.exists(analysis_path):
        try:
            os.remove(analysis_path)
        except Exception:
            pass

    return jsonify({"ok": True, "deleted": resume_id})

# ------------------------------
# AI Aids: Tailor Resume & Cover Letter
# ------------------------------
@app.post("/ai/refine_resume_for_job")
@jwt_required()
def ai_refine_resume_for_job():
    data = request.get_json(force=True, silent=True) or {}
    resume_id = data.get("resume_id")
    job = data.get("job") or {}
    if not resume_id:
        return jsonify({"error": "resume_id required"}), 400
    payload = DB["resumes"].get(resume_id)
    if not payload:
        json_path = f"./uploads/{resume_id}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    payload = json.load(jf)
                DB.setdefault("resumes", {})[resume_id] = payload
            except Exception:
                return jsonify({"error": "Resume could not be loaded from disk"}), 404
        else:
            return jsonify({"error": "Unknown resume_id"}), 404
    raw_text = payload.get("raw_text") or ""
    if not raw_text:
        return jsonify({"error": "No raw_text stored for this resume_id"}), 400
    result = refine_resume_for_job_llm(raw_text, job)
    return jsonify(result)

@app.post("/ai/cover_letter")
@jwt_required()
def ai_cover_letter():
    data = request.get_json(force=True, silent=True) or {}
    resume_id = data.get("resume_id")
    job = data.get("job") or {}
    if not resume_id:
        return jsonify({"error": "resume_id required"}), 400
    payload = DB["resumes"].get(resume_id)
    if not payload:
        json_path = f"./uploads/{resume_id}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    payload = json.load(jf)
                DB.setdefault("resumes", {})[resume_id] = payload
            except Exception:
                return jsonify({"error": "Resume could not be loaded from disk"}), 404
        else:
            return jsonify({"error": "Unknown resume_id"}), 404
    raw_text = payload.get("raw_text") or ""
    if not raw_text:
        return jsonify({"error": "No raw_text stored for this resume_id"}), 400
    result = generate_cover_letter_llm(raw_text, job)
    return jsonify(result)

# ------------------------------
# Entrypoint
# ------------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000, debug=app.config.get("DEBUG", False))
