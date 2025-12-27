# ---- Face metrics helpers ----
import time
from helpers import _now, _ema 


def _ensure_face_state(sess: dict):
    if "face" not in sess:
        sess["face"] = {
            "last_ts": None,
            "ema_attention": None,
            "ema_faces": None,
            "frames": 0,
            "smile_frames": 0,
            "present_frames": 0,       # frames with faces > 0
            "inattentive_since": None,
            "away_since": None,
            "nudges": 0,
            "nudged_this_question": False,
            "question_start_ts": _now(),
            "question_summaries": [],  # list per question
        }
    return sess["face"]

def _reset_per_question_face_state(sess: dict):
    st = _ensure_face_state(sess)
    # Push previous question summary if any frames were seen
    if st["frames"] > 0:
        sess["face"]["question_summaries"].append({
            "frames": st["frames"],
            "present_frames": st["present_frames"],
            "smile_frames": st["smile_frames"],
            "avg_attention": st["ema_attention"] if st["ema_attention"] is not None else 0.0,
            "duration_s": max(0, _now() - (st["question_start_ts"] or _now())),
            "nudged": st["nudged_this_question"],
        })
    # Reset rolling state for next question
    sess["face"].update({
        "last_ts": None,
        "ema_attention": None,
        "ema_faces": None,
        "frames": 0,
        "smile_frames": 0,
        "present_frames": 0,
        "inattentive_since": None,
        "away_since": None,
        "nudged_this_question": False,
        "question_start_ts": _now(),
    })

def _finalize_face_summary(sess: dict):
    st = _ensure_face_state(sess)
    # include current question if any frames collected
    if st["frames"] > 0:
        sess["face"]["question_summaries"].append({
            "frames": st["frames"],
            "present_frames": st["present_frames"],
            "smile_frames": st["smile_frames"],
            "avg_attention": st["ema_attention"] if st["ema_attention"] is not None else 0.0,
            "duration_s": max(0, _now() - (st["question_start_ts"] or _now())),
            "nudged": st["nudged_this_question"],
        })
    qs = sess["face"]["question_summaries"]
    # Aggregate totals
    total_frames = sum(q["frames"] for q in qs) or 1
    total_present = sum(q["present_frames"] for q in qs)
    total_smile = sum(q["smile_frames"] for q in qs)
    avg_attention = round(sum((q["avg_attention"] or 0) * q["frames"] for q in qs) / total_frames, 3)
    smile_ratio = round(total_smile / total_frames, 3)
    presence_ratio = round(total_present / total_frames, 3)
    return {
        "questions": qs,
        "overall": {
            "frames": total_frames,
            "presence_ratio": presence_ratio,   # ~% of frames with a detected face
            "smile_ratio": smile_ratio,         # ~% of frames smiling (if provided)
            "avg_attention": avg_attention,
            "nudges": sess["face"]["nudges"],
        }
    }
