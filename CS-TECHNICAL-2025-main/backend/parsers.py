# parsers.py
from __future__ import annotations
import io
import re
import unicodedata
from typing import Dict, Any, List, Tuple

from pypdf import PdfReader

# ----------------------------
# Utilities (case-insensitive & accent-insensitive)
# ----------------------------
def _cf(s: str) -> str:
    """Casefold for robust case-insensitive matching."""
    return (s or "").casefold()

def _strip_accents(s: str) -> str:
    try:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    except Exception:
        return s

def _norm_ci(s: str) -> str:
    """Casefold + accent-strip for comparisons."""
    return _cf(_strip_accents(s or ""))

# ----------------------------
# Regexes
# ----------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,})")

# ----------------------------
# Canonical dictionaries (keys in casefolded form)
# ----------------------------
COUNTRY_HINTS_TLD = {
    "tn": "Tunisia", "fr": "France", "de": "Germany", "uk": "United Kingdom",
    "gb": "United Kingdom", "us": "United States", "ca": "Canada",
    "es": "Spain", "it": "Italy", "ma": "Morocco", "dz": "Algeria",
    "sa": "Saudi Arabia", "ae": "United Arab Emirates", "in": "India",
}

EMEA = { _norm_ci(x) for x in [
    "Tunisia","France","Germany","United Kingdom","Spain","Italy",
    "Morocco","Algeria","Saudi Arabia","United Arab Emirates","Egypt",
    "Portugal","Netherlands","Belgium","Sweden","Norway","Denmark",
    "Finland","Switzerland","Austria","Poland","Czech Republic","Ireland",
    "Greece","Turkey","South Africa","Kenya","Nigeria","Ghana","UAE",
]}
AMER = { _norm_ci(x) for x in [
    "United States","Canada","Mexico","Brazil","Argentina","Chile","Colombia"
]}
APAC = { _norm_ci(x) for x in [
    "India","Japan","Singapore","Australia","New Zealand","South Korea","Indonesia","Philippines","Malaysia","Vietnam"
]}

CITY_TO_COUNTRY = {
    # Common capitals/cities (add freely; matching is case-insensitive)
    "tunis": "Tunisia", "paris": "France", "lyon": "France", "berlin": "Germany",
    "madrid": "Spain", "barcelona": "Spain", "rome": "Italy", "milan": "Italy",
    "london": "United Kingdom", "manchester": "United Kingdom",
    "cairo": "Egypt", "casablanca": "Morocco", "rabat": "Morocco",
    "riyadh": "Saudi Arabia", "dubai": "United Arab Emirates", "abu dhabi": "United Arab Emirates",
    "new york": "United States", "san francisco": "United States", "toronto": "Canada",
    "bangalore": "India", "bengaluru": "India", "singapore": "Singapore", "sydney": "Australia",
}

# Canonical skills; keys are casefolded aliases; values are canonical lowercase tokens
SKILL_CANON = {
    "py": "python", "python3": "python", "py3": "python",
    "js": "javascript", "node": "nodejs", "node.js": "nodejs",
    "ts": "typescript",
    "reactjs": "react", "react": "react", "next": "next.js", "nextjs": "next.js",
    "vuejs": "vue", "vue": "vue", "angular": "angular",
    "tf": "tensorflow", "tfjs": "tensorflow", "tensorflow.js": "tensorflow",
    "pytorch": "pytorch", "sklearn": "scikit-learn", "scikit learn": "scikit-learn",
    "opencv": "opencv", "nlp": "nlp", "computer vision": "computer vision",
    "pandas": "pandas", "numpy": "numpy",
    "sql": "sql", "postgres": "postgresql", "postgresql": "postgresql", "mysql": "mysql",
    "mongodb": "mongodb", "redis": "redis", "rabbitmq": "rabbitmq",
    "docker": "docker", "k8s": "kubernetes", "kubernetes": "kubernetes",
    "aws": "aws", "gcp": "gcp", "azure": "azure",
    "fast api": "fastapi", "fast-api": "fastapi", "fastapi": "fastapi",
    "flask": "flask", "django": "django",
    "rest": "rest", "graphql": "graphql",
    "airflow": "airflow", "spark": "spark",
    "git": "git", "linux": "linux", "bash": "bash", "ci": "ci", "cd": "cd",
}

# When scanning free text, keep hits only if in this allowlist (casefolded)
TECH_ALLOWLIST = { *SKILL_CANON.values(), *[
    "java","c++","c#","go","rust","react","next.js","vue","angular",
    "docker","kubernetes","aws","gcp","azure","postgresql","mysql","mongodb",
    "redis","rabbitmq","tensorflow","pytorch","scikit-learn","opencv","nlp","computer vision",
    "pandas","numpy","sql","fastapi","flask","django","rest","graphql","airflow","spark",
    "git","linux","bash","ci","cd","nodejs","typescript","javascript"
]}

ROLE_WORDS = [
    "backend", "frontend", "full stack", "full-stack", "machine learning", "ml engineer", "data engineer",
    "data scientist", "devops", "cloud engineer", "security", "ios", "android", "mobile", "ai engineer",
    "qa", "test engineer", "product manager", "technical writer", "game developer"
]

SECTION_HEADERS = [
    "education", "experience", "work experience", "skills", "projects", "summary", "profile"
]

# ----------------------------
# Helpers
# ----------------------------
def _clean_text(b: bytes) -> str:
    """Fallback text decoding if bytes are already text-like.

    For PDFs we prefer PdfReader below, but keep this for .txt/docx fallbacks
    or already-decoded content.
    """
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return b.decode("latin1", errors="ignore")


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract visible text from a PDF using pypdf.

    This ignores images (no OCR), but grabs all text from all pages.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        chunks: List[str] = []
        for idx, page in enumerate(reader.pages):
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t:
                chunks.append(t)
        text = "\n".join(chunks)
        print(f"[parsers] PDF text length: {len(text)} chars")
        return text
    except Exception as e:
        print(f"[parsers] PdfReader failed: {e}")
        # Fall back to naive decoding if PDF parsing fails
        return _clean_text(file_bytes)

def _extract_email_domain(text: str) -> Tuple[str, str]:
    m = EMAIL_RE.search(text or "")
    if not m:
        return "", ""
    domain = m.group(1)
    return m.group(0), domain

def _tld_to_country(tld: str) -> str:
    t = (tld or "").split(".")[-1].lower()
    return COUNTRY_HINTS_TLD.get(t, "")

def _infer_region(country: str) -> str:
    c = _norm_ci(country)
    if not c: return "Remote"
    if c in EMEA: return "EMEA"
    if c in AMER: return "AMER"
    if c in APAC: return "APAC"
    return "Remote"

def _naive_sections(text: str) -> Dict[str, str]:
    """Very lightweight section splitter based on common headings.

    Keeps the original casing/text but indexes by lower-cased header name
    ("experience", "education", "skills", etc.).
    """
    lower = _cf(text)
    idxs: List[Tuple[int, str]] = []
    for h in SECTION_HEADERS:
        i = lower.find(_cf(h))
        if i != -1:
            idxs.append((i, h))
    idxs.sort()
    sections: Dict[str, str] = {}
    for n, (start, name) in enumerate(idxs):
        end = idxs[n + 1][0] if n + 1 < len(idxs) else len(text)
        # strip the header label itself if it is at the start of the slice
        block = text[start:end].strip()
        header = name.lower()
        sections[header] = block
    return sections


def _extract_summary(sections: Dict[str, str]) -> str:
    """Return a short summary/profile paragraph if present."""
    for key in ("summary", "profile"):
        block = sections.get(key)
        if not block:
            continue
        # Drop the heading line itself; keep the first 3–4 lines joined.
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        # Heuristic: skip the first line if it basically *is* the header label
        first = lines[0]
        if _cf(key) in _cf(first) and len(lines) > 1:
            lines = lines[1:]
        summary = " ".join(lines[:4]).strip()
        return summary[:1000]
    return ""


def _extract_education(sections: Dict[str, str]) -> List[Dict[str, Any]]:
    """Parse a loose list of education entries from the education section.

    Output is intentionally simple and robust:
    [{"institution": ..., "degree": ..., "years": ...}, ...]
    """
    block = sections.get("education") or ""
    if not block:
        return []

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    # Drop heading-like first line
    if lines and _cf("education") in _cf(lines[0]):
        lines = lines[1:]

    entries: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    DATE_RE = re.compile(r"(20\d{2}|19\d{2})")

    for ln in lines:
        if not current:
            current = {"institution": ln, "degree": "", "years": ""}
        else:
            # Attach degree/years hints to current entry
            if any(k in _cf(ln) for k in ["bachelor", "master", "phd", "licence", "ingénieur", "engineer"]):
                current["degree"] = (current.get("degree") or "") or ln
            if DATE_RE.search(ln):
                years = current.get("years") or ""
                current["years"] = (years + "; " + ln) if years else ln

        # Heuristic: blank lines (already removed) or bullets would normally
        # separate entries; here we just split when line looks like a new school.
        if "," in ln and len(ln.split()) <= 8 and DATE_RE.search(ln) is None:
            # treat as boundary; flush previous if we already had institution
            if current:
                entries.append(current)
                current = {}

    if current:
        entries.append(current)
    return entries[:10]


def _extract_experience(sections: Dict[str, str]) -> List[Dict[str, Any]]:
    """Parse experience/work experience into a list of simple roles.

    Each role: {"title", "company", "location", "start", "end", "bullets"}.
    This is heuristic but good enough for downstream analytics.
    """
    block = sections.get("experience") or sections.get("work experience") or ""
    if not block:
        return []

    lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
    # Drop heading-like first line
    first = lines[0] if lines else ""
    if first and any(_cf(h) in _cf(first) for h in ["experience", "work experience"]):
        lines = lines[1:]

    DATE_RANGE_RE = re.compile(r"(19|20)\d{2}.*?(present|now|\d{4})", re.I)
    BULLET_PREFIX_RE = re.compile(r"^\s*[-•*]\s+")

    roles: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {"title": "", "company": "", "location": "", "start": "", "end": "", "bullets": []}

    def flush_current():
        nonlocal current
        if any(current.get(k) for k in ("title", "company", "bullets")):
            # trim bullet text
            current["bullets"] = [b.strip() for b in current.get("bullets", []) if b.strip()]
            roles.append(current)
        current = {"title": "", "company": "", "location": "", "start": "", "end": "", "bullets": []}

    for ln in lines:
        raw = ln.strip()

        # Bullet line → add to bullets of current role
        if raw.startswith("-") or raw.startswith("•") or raw.startswith("*"):
            current.setdefault("bullets", []).append(raw.lstrip("-•* "))
            continue

        # Look for date ranges like "2020 - Present" or "2018 – 2022"
        m = DATE_RANGE_RE.search(raw)
        if m:
            # simplistic split: first year = start, last token = end
            years = re.findall(r"(19|20)\d{2}", raw)
            if years:
                current["start"] = years[0][0] + years[0][1:] if isinstance(years[0], tuple) else years[0]
                if len(years) > 1:
                    last = years[-1]
                    current["end"] = last[0] + last[1:] if isinstance(last, tuple) else last
                else:
                    current["end"] = "Present"
            continue

        # If line looks like "Title, Company – Location" or similar
        if "," in raw and (" - " in raw or " – " in raw):
            flush_current()
            # Split on first comma for title vs rest
            title_part, rest = raw.split(",", 1)
            current["title"] = title_part.strip()
            # Split rest on dash for company vs location
            if " - " in rest:
                company_part, loc_part = rest.split(" - ", 1)
            elif " – " in rest:
                company_part, loc_part = rest.split(" – ", 1)
            else:
                company_part, loc_part = rest, ""
            current["company"] = company_part.strip()
            current["location"] = loc_part.strip()
            continue

        # Fallback: if line has a lot of words and no bullets yet, treat as title/company
        if len(raw.split()) <= 8 and not current.get("title"):
            current["title"] = raw
        else:
            current.setdefault("bullets", []).append(raw)

    flush_current()
    return roles[:12]

def _guess_name(lines: List[str]) -> str:
    for ln in lines[:5]:
        if "@" in ln: 
            continue
        t = re.sub(r"[^A-Za-z\s.'-]", "", ln).strip()
        if t and len(t.split()) <= 5:
            return t[:80]
    return ""

def _normalize_skill_token(tok: str) -> str:
    """Return canonical lowercase token for a skill token, ignoring case and accents."""
    raw = (tok or "").strip()
    if not raw: return ""
    cf = _norm_ci(raw)
    # normalize punctuation spaces: "fast api" -> "fast api"
    cf = re.sub(r"\s+", " ", cf)
    # map aliases
    if cf in SKILL_CANON:
        return SKILL_CANON[cf]
    return cf  # fallback: already casefolded canonical

def _extract_skills(text: str, sections: Dict[str, str]) -> List[str]:
    """
    Pull skills from:
      1) Skills section (if present)
      2) Anywhere in text by scanning words/phrases and matching allowlist
    Normalize case (handles Python/PYTHON/Py → python, etc.)
    """
    # 1) from skills section
    block = sections.get("skills", "") or ""
    raw = re.split(r"[,;/|\n•\-]\s*", block)
    prelim = []
    for tok in raw:
        norm = _normalize_skill_token(tok)
        if not norm: 
            continue
        # Keep only tech tokens
        if norm in TECH_ALLOWLIST:
            prelim.append(norm)

    # 2) from entire text (catch capitalized tokens like "Python", "PostgreSQL")
    # Find tokens and 2-grams likely to be tech
    txt_cf = _norm_ci(text)
    # normalize some punctuation to space
    txt_cf = re.sub(r"[^a-z0-9+#.\s-]", " ", txt_cf)
    candidates = set()
    # single tokens
    for m in re.finditer(r"\b[a-z0-9+#.]{2,}\b", txt_cf):
        candidates.add(m.group(0))
    # bigrams like "computer vision", "fast api"
    words = txt_cf.split()
    for i in range(len(words)-1):
        bg = f"{words[i]} {words[i+1]}"
        if 3 <= len(bg) <= 30:
            candidates.add(bg)

    for tok in candidates:
        norm = _normalize_skill_token(tok)
        if norm in TECH_ALLOWLIST:
            prelim.append(norm)

    # de-duplicate case-insensitively while preserving canonical lowercase
    out, seen = [], set()
    for s in prelim:
        key = _norm_ci(s)
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out[:60]

def _extract_roles(text: str) -> List[str]:
    low = _cf(text)
    hits, seen = [], set()
    for r in ROLE_WORDS:
        if _cf(r) in low and _cf(r) not in seen:
            hits.append(_cf(r)); seen.add(_cf(r))
    return hits[:5]

def _extract_phone(text: str) -> str:
    m = PHONE_RE.search(text or "")
    return m.group(1).strip() if m else ""

def _find_location(lines: List[str], text: str) -> Tuple[str, str]:
    """
    Return (city_or_hint, country_guess). Matches are case-insensitive.
    """
    # Look in top header lines first
    for ln in lines[:8]:
        cf = _norm_ci(ln)
        for city, country in CITY_TO_COUNTRY.items():
            if city in cf:
                return (ln.strip(), country)

    # Search the whole text for explicit country names (case-insensitive)
    low = _norm_ci(text)
    for country in list(EMEA) + list(AMER) + list(APAC):
        # country already normalized; compare to normalized text
        if country and country in low:
            # return the original-cased best-effort country name
            return (country.title(), country.title())

    return ("", "")

# ----------------------------
# Main entry
# ----------------------------
def parse_resume_bytes(file_bytes: bytes) -> Dict[str, Any]:
    # Try PDF extraction first; if that fails or yields too little, fall back
    # to simple decoding.
    text = _extract_text_from_pdf(file_bytes)
    if len(text.strip()) < 50:  # likely bad extraction
        print("[parsers] PDF text too short, falling back to naive decode")
        text = _clean_text(file_bytes)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    email, domain = _extract_email_domain(text)
    phone = _extract_phone(text)
    name_guess = _guess_name(lines)

    # Country via TLD (case-insensitive)
    country_tld = _tld_to_country(domain or "")
    # Country via content (case-insensitive city/country scan)
    city_or_hint, country_scan = _find_location(lines, text)

    country = country_scan or country_tld
    region = _infer_region(country)

    sections = _naive_sections(text)
    skills = _extract_skills(text, sections)
    roles = _extract_roles(text)
    summary = _extract_summary(sections)
    education = _extract_education(sections)
    experience = _extract_experience(sections)

    # Best-effort location string prioritizing specific hints
    location = city_or_hint or country or region or "Remote"

    return {
        "candidate": {"name": name_guess, "email": email, "phone": phone, "links": []},
        "skills": {"hard": skills, "soft": []},     # skills come back canonicalized in lowercase
        "roles": roles,                              # already casefolded
        "location": location,                        # best-effort, keeps original casing for city hint
        "region": region,                            # EMEA/AMER/APAC/Remote
        "education": education,
        "experience": experience,
        "summary": summary,
        "raw_text": text[:200000],
    }
