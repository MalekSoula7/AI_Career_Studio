# auth.py
from __future__ import annotations
import os, re
from datetime import timedelta
from typing import List

from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from auth_store import find_user, create_user, verify_password, seed_admin

auth_bp = Blueprint("auth", __name__)

# rate limiter; will be bound to app in init_auth()
limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])

# CORS origins for these endpoints
DEFAULT_ORIGINS = [
    "http://localhost:3000","http://127.0.0.1:3000",
    "http://localhost:5173","http://127.0.0.1:5173",
]
def _origins():
    raw = os.getenv("CORS_ORIGINS", "")
    # Allow quick dev override for everything
    if raw.strip() == "*":
        return "*"
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    # When running in debug mode, allow wildcard for convenience in dev
    try:
        if current_app and current_app.config.get("DEBUG"):
            return "*"
    except RuntimeError:
        # current_app may not be available at import time
        pass
    return DEFAULT_ORIGINS

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _password_ok(p: str) -> bool:
    # Min 8 chars, at least 1 letter & 1 digit (tune as needed)
    return bool(len(p) >= 8 and re.search(r"[A-Za-z]", p) and re.search(r"\d", p))

@auth_bp.route("/login", methods=["POST","OPTIONS"], strict_slashes=False)
@cross_origin(origins=_origins(), allow_headers=["Content-Type","Authorization"],
              methods=["POST","OPTIONS"], max_age=600)
@limiter.limit("10/minute")
def login():
    """
    Request: { "email": "...", "password": "..." }
    Response: { "access_token": "...", "token_type": "Bearer", "expires_in": 900 }
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error":"email and password are required"}), 400

    user = find_user(email)
    if not user or not verify_password(password, user.get("pw_hash","")):
        return jsonify({"error":"invalid credentials"}), 401

    claims = {"roles": user.get("roles", []), "email": user["email"]}
    token = create_access_token(identity=user["email"], additional_claims=claims, expires_delta=timedelta(minutes=15))
    return jsonify({"access_token": token, "token_type":"Bearer", "expires_in": 900}), 200

@auth_bp.route("/register", methods=["POST","OPTIONS"], strict_slashes=False)
@cross_origin(origins=_origins(), allow_headers=["Content-Type","Authorization"],
              methods=["POST","OPTIONS"], max_age=600)
@limiter.limit("5/minute")
def register():
    """
    Request: { "email": "...", "password": "...", "name": "..." }
    Auto-logs in on success with a short-lived JWT.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()

    if not email or not password:
        return jsonify({"error":"email and password are required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error":"invalid email format"}), 400
    if not _password_ok(password):
        return jsonify({"error":"password too weak (min 8 chars, include letters & digits)"}), 400

    try:
        create_user(email, password, name=name, roles=["user"])
    except ValueError as e:
        if str(e) == "email_already_exists":
            # generic message to reduce enumeration risk
            return jsonify({"error":"unable to create account"}), 409
        raise

    token = create_access_token(identity=email, additional_claims={"roles":["user"], "email": email},
                                expires_delta=timedelta(minutes=15))
    return jsonify({"access_token": token, "token_type":"Bearer", "expires_in": 900}), 201

# Optional: seed admin from env on startup (call from init_auth)
def _maybe_seed_admin_from_env():
    admin_email = os.getenv("ADMIN_EMAIL") or ""
    admin_pw    = os.getenv("ADMIN_PASSWORD") or ""
    if admin_email and admin_pw:
        seed_admin(admin_email, admin_pw)

def init_auth(app):
    """
    Call once from app.py:
        from auth import auth_bp, init_auth
        app.register_blueprint(auth_bp, url_prefix="/auth")
        init_auth(app)
    """
    limiter.init_app(app)
    _maybe_seed_admin_from_env()
