# auth_store.py
from __future__ import annotations
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from passlib.hash import bcrypt, bcrypt_sha256, pbkdf2_sha256 # <-- add bcrypt_sha256
from pymongo import MongoClient, ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError
from bson import ObjectId


# -------- Mongo connection --------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB", "cs_chall")

_client: Optional[MongoClient] = None
_db = None

def _get_db():
    global _client, _db
    if _db is not None:
        return _db
    _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    _db = _client[MONGO_DB]
    # Ensure indexes once
    _db.users.create_index([("email", ASCENDING)], unique=True, name="uniq_email")
    _db.resumes.create_index([("user_id", ASCENDING)], name="resumes_user")
    _db.resumes.create_index([("created_at", ASCENDING)], name="resumes_created")
    _db.sessions.create_index([("user_id", ASCENDING)], name="sessions_user")
    return _db

# -------- Users --------
def find_user(email: str) -> Optional[Dict[str, Any]]:
    db = _get_db()
    return db.users.find_one({"email": (email or "").lower().strip()})

def _hash_password(pw: str) -> str:
    # strong defaults: 29000+ rounds; can set .using(rounds=...) if desired
    return pbkdf2_sha256.hash(pw)

def verify_password(pw: str, pw_hash: str) -> bool:
    try:
        return pbkdf2_sha256.verify(pw, pw_hash)
    except Exception:
        return False

def create_user(email: str, password: str, name: str = "", roles: Optional[List[str]] = None) -> Dict[str, Any]:
    roles = roles or ["user"]
    db = _get_db()
    doc = {
        "email": (email or "").lower().strip(),
        "pw_hash": _hash_password(password),  # <-- use bcrypt_sha256
        "name": (name or "").strip(),
        "roles": roles,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    try:
        db.users.insert_one(doc)
        return doc
    except DuplicateKeyError:
        raise ValueError("email_already_exists")

def seed_admin(email: str, password: str, name: str = "Admin") -> Dict[str, Any]:
    db = _get_db()
    email_n = (email or "").lower().strip()
    pw_hash = _hash_password(password)       # <-- use bcrypt_sha256
    doc = db.users.find_one_and_update(
        {"email": email_n},
        {"$set": {"email": email_n, "name": name, "roles": ["admin"], "pw_hash": pw_hash, "updated_at": datetime.utcnow()},
         "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return doc
# -------- Resumes (metadata; blob stored encrypted on disk/S3) --------
def save_resume(user_email: str, enc_path: str, mime: str, meta: Dict[str, Any]) -> str:
    db = _get_db()
    user = find_user(user_email)
    if not user:
        raise ValueError("unknown_user")
    doc = {
        "user_id": user["_id"],
        "user_email": user["email"],
        "enc_path": enc_path,  # e.g., ./uploads/<rid>_<safe>.enc or s3://...
        "mime": mime,
        "meta": meta,          # parsed resume structure (JSON)
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    res = db.resumes.insert_one(doc)
    return str(res.inserted_id)

def get_resume(resume_id: str) -> Optional[Dict[str, Any]]:
    db = _get_db()
    try:
        oid = ObjectId(resume_id)
    except Exception:
        return None
    doc = db.resumes.find_one({"_id": oid})
    if not doc:
        return None
    # stringify id for JSON
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc

def list_resumes_for_user(user_email: str, limit: int = 50) -> List[Dict[str, Any]]:
    db = _get_db()
    cur = db.resumes.find({"user_email": (user_email or "").lower().strip()}).sort("created_at", -1).limit(limit)
    out = []
    for d in cur:
        d["id"] = str(d["_id"]); del d["_id"]
        out.append(d)
    return out
