import uuid

DB = {
    "files": {},     # resume_id -> bytes
    "resumes": {},   # resume_id -> parsed dict
    "sessions": {},  # session_id -> state dict
}

def new_id() -> str:
    return str(uuid.uuid4())
