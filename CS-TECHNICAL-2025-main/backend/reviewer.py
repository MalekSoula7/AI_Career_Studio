# reviewer.py
import re
from typing import Dict, Any, List
from collections import Counter

ACTION_VERBS = [
    "built","designed","implemented","launched","migrated","refactored",
    "optimized","reduced","increased","automated","integrated","owned",
    "led","mentored","delivered","deployed","scaled","monitored","tested"
]
TECH_HINTS = [
    "python","javascript","typescript","java","c++","go","rust","react","node","fastapi","flask",
    "django","postgres","mysql","mongodb","redis","docker","kubernetes","aws","gcp","azure",
    "graphql","rest","airflow","spark","pytorch","tensorflow","sklearn","linux","bash","git","ci","cd"
]
FILLERS = ["passionate","hard-working","fast learner","self-starter","innovative","synergy","rockstar"]

NUMERIC_RE = re.compile(r"\b(\d+(\.\d+)?%|\d{2,})\b")
BULLET_RE = re.compile(r"(^\s*[-•*]\s+.+)", re.M)
SENT_END_RE = re.compile(r"[.!?]+")

def _fk_grade(text: str) -> float:
    # Very light readability proxy (not exact FK)
    words = max(1, len(re.findall(r"\w+", text)))
    sents = max(1, len(SENT_END_RE.findall(text)))
    avgw = words / sents
    return round(4.0 + 0.6 * min(25, avgw), 1)

def _has_section(text: str, name: str) -> bool:
    return name.lower() in text.lower()

def _count_action_verbs(text: str) -> int:
    low = text.lower()
    return sum(1 for v in ACTION_VERBS if re.search(rf"\b{re.escape(v)}\b", low))

def _collect_bullets(text: str) -> List[str]:
    return [m.strip() for m in BULLET_RE.findall(text)]

def _score_ats(text: str) -> int:
    score = 40
    low = text.lower()

    # Sections
    for s in ("education","experience","skills","projects","summary","profile","work experience"):
        if _has_section(text, s): score += 4

    # Length / density
    n_words = len(re.findall(r"\w+", text))
    if 700 <= n_words <= 1200: score += 8
    elif 400 <= n_words < 700 or 1200 < n_words <= 1800: score += 4

    # Action verbs & numbers
    score += min(12, _count_action_verbs(text))  # cap
    if len(NUMERIC_RE.findall(text)) >= 6: score += 10
    elif len(NUMERIC_RE.findall(text)) >= 3: score += 6

    # Concrete tech
    tech_hits = sum(1 for t in TECH_HINTS if re.search(rf"\b{re.escape(t)}\b", low))
    score += min(12, tech_hits // 3 * 2)

    # Bullets
    bullets = _collect_bullets(text)
    if len(bullets) >= 8: score += 8
    elif len(bullets) >= 4: score += 4

    return max(0, min(100, score))

def _find_gaps(text: str) -> List[str]:
    gaps = []
    low = text.lower()

    if not _has_section(text,"experience"):
        gaps.append("Add an Experience/Work Experience section.")
    if not _has_section(text,"skills"):
        gaps.append("Include a Skills section with concrete tools & levels.")
    if not _collect_bullets(text):
        gaps.append("Use bullet points for achievements (1–2 lines each).")
    if len(NUMERIC_RE.findall(text)) < 3:
        gaps.append("Quantify impact (%, time, cost, users, latency).")
    if _count_action_verbs(text) < 5:
        gaps.append("Start bullets with strong action verbs (Built, Reduced, Led).")
    if any(f in low for f in FILLERS):
        gaps.append("Remove filler words (e.g., “passionate”, “rockstar”).")
    return gaps

def _rewrite_summary_from_text(text: str, parsed: Dict[str, Any]) -> str:
    # Prefer structured hard skills if available, otherwise fall back to raw text scan
    structured_skills = (parsed.get("skills") or {}).get("hard") or []
    if structured_skills:
        hits = [s.lower() for s in structured_skills]
    else:
        hits = [t for t in TECH_HINTS if re.search(rf"\b{re.escape(t)}\b", text.lower())]
    top = [w for w, _ in Counter(hits).most_common(6)]
    tech_str = ", ".join(top) if top else "modern backend and cloud tooling"
    return (
        f"Engineer with hands-on delivery across APIs, automation, and reliability. "
        f"Focus on measurable outcomes (performance, cost, uptime). Core stack: {tech_str}."
    )

def _rewrite_bullets_from_text(text: str) -> List[str]:
    # Turn free text into 3 sample, impact-focused bullets
    bullets = []
    candidates = [ln.strip("-•* ").strip() for ln in text.splitlines() if len(ln.strip()) > 0]
    sample = [c for c in candidates if len(c.split()) > 5][:8]
    for s in sample[:3]:
        bullets.append(f"• {re.sub(r'[.]+$', '', s)} (measured via latency/errors/users; add %/ms).")
    if not bullets:
        bullets = [
            "• Built and deployed REST APIs; reduced P95 latency by 35% by optimizing queries and caching.",
            "• Automated CI/CD with GitHub Actions and Docker; cut release lead time from weekly to daily.",
            "• Migrated services to AWS; lowered monthly cost by 22% via rightsizing and storage lifecycle."
        ]
    return bullets

def reviewer(parsed: Dict[str, Any]) -> Dict[str, Any]:
    text = parsed.get("raw_text", "") or ""
    ats = _score_ats(text)
    grade = _fk_grade(text)
    gaps = _find_gaps(text)
    dup_buzz = [w for w in FILLERS if w in text.lower()]

    rewrite = {
        "summary": _rewrite_summary_from_text(text, parsed),
        "sample_bullets": _rewrite_bullets_from_text(text),
        "tips": [
            "Keep bullets to ~1–2 lines each; one action, one result.",
            "Front-load metrics (%, time, cost, users) and name the tools.",
            "Use consistent tense (past for completed work, present for current).",
        ],
    }

    # minimal quality flags for the UI
    flags = {
        "has_experience": _has_section(text,"experience") or _has_section(text,"work experience"),
        "has_skills": _has_section(text,"skills"),
        "bullets_count": len(_collect_bullets(text)),
        "numbers_count": len(NUMERIC_RE.findall(text)),
        "action_verbs_count": _count_action_verbs(text),
        "word_count": len(re.findall(r'\w+', text)),
    }

    return {
        "ats_score": ats,
        "readability": {"fk_grade": grade},
        "flags": flags,
        "gaps": gaps,
        "duplicate_buzzwords": dup_buzz,
        "rewrite": rewrite
    }
