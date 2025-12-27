from typing import List, Dict, Any, Optional, Iterable, Set
from sources.noauth_jobs import all_sources

# ---------------------------------------------
# Regional filters (MENA and Sub-Saharan Africa)
# ---------------------------------------------
MENA_COUNTRIES = {
    "algeria", "bahrain", "djibouti", "egypt", "iran", "iraq", "israel",
    "jordan", "kuwait", "lebanon", "libya", "mauritania", "morocco", "oman",
    "palestine", "qatar", "saudi arabia", "ksa", "syria", "tunisia",
    "united arab emirates", "uae", "yemen", "sudan", "western sahara"
}

SSA_COUNTRIES = {
    "angola", "benin", "botswana", "burkina faso", "burundi", "cabo verde",
    "cameroon", "central african republic", "car", "chad", "comoros",
    "congo", "republic of the congo", "dr congo", "democratic republic of the congo",
    "cote d'ivoire", "ivory coast", "equatorial guinea", "eritrea", "eswatini",
    "ethiopia", "gabon", "gambia", "ghana", "guinea", "guinea-bissau",
    "kenya", "lesotho", "liberia", "madagascar", "malawi", "mali",
    "mauritius", "mozambique", "namibia", "niger", "nigeria", "rwanda",
    "sao tome", "sao tome and principe", "senegal", "seychelles", "sierra leone",
    "somalia", "south africa", "south sudan", "tanzania", "togo", "uganda",
    "zambia", "zimbabwe"
}

REGION_KEYWORDS = {
    "mena": {"mena", "middle east", "north africa"} | MENA_COUNTRIES,
    "ssa": {"ssa", "sub-saharan africa", "sub saharan africa"} | SSA_COUNTRIES,
}

def _lc(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def _normalize_region(region: Optional[str]) -> Optional[str]:
    if not region:
        return None
    r = region.strip().lower()
    # Direct keys
    if r in REGION_KEYWORDS:
        return r
    # Common synonyms / phrasing
    if "mena" in r or "middle east" in r or "north africa" in r:
        return "mena"
    if "ssa" in r or ("sub" in r and "sahar" in r):
        return "ssa"
    # Treat generic "africa" as SSA for this challenge context
    if r == "africa" or "africa" in r:
        return "ssa"
    return None  # unknown / other region

def _normalize_mode(mode: Optional[str]) -> str:
    m = (mode or "").strip().lower()
    if m in {"remote", "remote_only", "fully remote", "remote-only"}:
        return "remote"
    if m in {"onsite", "on-site", "office"}:
        return "onsite"
    return "any"

def _is_remote(job: Dict[str, Any]) -> bool:
    loc = _lc(job.get("location"))
    tags = { _lc(t) for t in (job.get("tags") or []) }
    text = " ".join([_lc(job.get("title")), _lc(job.get("company")), loc, _lc(job.get("snippet"))])
    return ("remote" in loc) or ("remote" in text) or ("remote" in tags)

def _tokenize_tags_from_title(title: str) -> Set[str]:
    # Very light tokenization from title to help when tags are sparse
    import re
    toks = set(re.findall(r"[a-zA-Z0-9+.#-]+", title.lower()))
    # common normalizations
    alias = {
        "py": "python", "python3": "python",
        "js": "javascript", "node.js": "nodejs", "node": "nodejs",
        "ts": "typescript", "tf": "tensorflow", "tfjs": "tensorflow",
        "postgres": "postgresql", "fast api": "fastapi", "fast-api": "fastapi",
    }
    return { alias.get(t, t) for t in toks }

def _region_country_filter(
    jobs: List[Dict[str, Any]],
    region: Optional[str] = None,
    countries: Optional[List[str]] = None,
    mode: str = "any",  # "remote" | "onsite" | "any"
) -> List[Dict[str, Any]]:
    # If truly no geo preference and mode is any, skip filtering
    if region is None and not countries and mode == "any":
        return jobs

    region_key = _normalize_region(region)
    region_set = REGION_KEYWORDS.get(region_key or "", set())

    custom_country_set = { _lc(c) for c in (countries or []) if c }

    # If user gave a region string that we don't map (e.g. "Tunisia"),
    # treat it as a direct substring filter rather than silently dropping it.
    if region and not region_key:
        custom_country_set.add(_lc(region))

    targets: Set[str] = region_set | custom_country_set

    def matches_geo(j: Dict[str, Any]) -> bool:
        # If user explicitly gave region/countries but we somehow ended up with
        # no targets, be strict and reject rather than include everything.
        if not targets:
            return False
        hay = " ".join([
            _lc(j.get("location")),
            _lc(j.get("title")),
            _lc(j.get("snippet")),
            " ".join(_lc(t) for t in (j.get("tags") or [])),
        ])
        return any(k in hay for k in targets)

    out: List[Dict[str, Any]] = []
    mode_n = _normalize_mode(mode)
    for j in jobs:
        remote = _is_remote(j)
        geo_ok = matches_geo(j)

        if mode_n == "remote":
            if remote and geo_ok:
                out.append(j)
        elif mode_n == "onsite":
            if geo_ok and not remote:
                out.append(j)
        else:  # "any"
            if geo_ok:
                out.append(j)

    return out

# Curated fallback jobs to ensure a diversified list when scraping is limited
FALLBACK_JOBS = [
    {"title":"Backend Engineer (Python/FastAPI)","company":"NimbusCloud","location":"Remote","url":"https://jobs.example.com/nimbus-backend","source":"Curated","tags":["python","fastapi","postgresql","docker"]},
    {"title":"Fullstack Developer (React/Node)","company":"AcmeTech","location":"Remote","url":"https://jobs.example.com/acme-fullstack","source":"Curated","tags":["react","nodejs","typescript","aws"]},
    {"title":"Data Scientist","company":"Insight Labs","location":"US","url":"https://jobs.example.com/insight-ds","source":"Curated","tags":["python","pandas","scikit-learn","ml"]},
    {"title":"Machine Learning Engineer","company":"VisionAI","location":"EU","url":"https://jobs.example.com/vision-ml","source":"Curated","tags":["pytorch","tensorflow","mlops","kubernetes"]},
    {"title":"DevOps Engineer","company":"PipeOps","location":"Remote","url":"https://jobs.example.com/pipeops-devops","source":"Curated","tags":["aws","terraform","kubernetes","ci/cd"]},
    {"title":"Frontend Engineer (Next.js)","company":"PixelCraft","location":"Remote","url":"https://jobs.example.com/pixel-frontend","source":"Curated","tags":["react","nextjs","tailwind","typescript"]},
    {"title":"Mobile Engineer (React Native)","company":"MoveFast","location":"Remote","url":"https://jobs.example.com/movefast-mobile","source":"Curated","tags":["react native","typescript","android","ios"]},
    {"title":"Cloud Engineer","company":"SkyScale","location":"US","url":"https://jobs.example.com/skyscale-cloud","source":"Curated","tags":["aws","gcp","azure","networking"]},
    {"title":"Security Engineer","company":"ShieldSec","location":"EU","url":"https://jobs.example.com/shield-security","source":"Curated","tags":["security","siem","sast","owasp"]},
    {"title":"QA Automation Engineer","company":"QualityWorks","location":"Remote","url":"https://jobs.example.com/qw-qa","source":"Curated","tags":["cypress","playwright","jest","selenium"]},
    {"title":"SRE","company":"Reliant","location":"Remote","url":"https://jobs.example.com/reliant-sre","source":"Curated","tags":["observability","prometheus","grafana","k8s"]},
    {"title":"Data Engineer","company":"DataForge","location":"Remote","url":"https://jobs.example.com/df-de","source":"Curated","tags":["spark","airflow","python","sql"]},
    {"title":"Platform Engineer","company":"CoreStack","location":"Remote","url":"https://jobs.example.com/corestack-platform","source":"Curated","tags":["platform","kubernetes","golang","terraform"]},
    {"title":"AI Product Manager","company":"NovaAI","location":"Remote","url":"https://jobs.example.com/novaai-pm","source":"Curated","tags":["ai","product","nlp","cv"]},
    {"title":"Backend Engineer (Go)","company":"Streamly","location":"Remote","url":"https://jobs.example.com/streamly-go","source":"Curated","tags":["golang","grpc","microservices","docker"]},
    {"title":"Fullstack (Django/React)","company":"GreenField","location":"Remote","url":"https://jobs.example.com/greenfield-fullstack","source":"Curated","tags":["django","react","postgresql","redis"]},
    {"title":"NLP Engineer","company":"TextWorks","location":"Remote","url":"https://jobs.example.com/textworks-nlp","source":"Curated","tags":["nlp","transformers","python","ml"]},
    {"title":"Computer Vision Engineer","company":"VisionWorks","location":"Remote","url":"https://jobs.example.com/visionworks-cv","source":"Curated","tags":["opencv","pytorch","cv","ml"]},
    {"title":"BI Analyst","company":"Metricly","location":"Remote","url":"https://jobs.example.com/metricly-bi","source":"Curated","tags":["sql","tableau","powerbi","analytics"]},
    {"title":"Backend Engineer (Java/Spring)","company":"EnterpriseSoft","location":"US","url":"https://jobs.example.com/enterprisesoft-java","source":"Curated","tags":["java","spring","microservices","kafka"]}
]


def _jaccard(a: set, b: set) -> float:
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def _build_explanation(
    resume_skills: Set[str],
    job_tags: Set[str],
    title: str,
    region: Optional[str],
    mode: str,
    remote: bool,
    country_hit: bool
) -> Dict[str, Any]:
    overlap = resume_skills & job_tags
    missing = [t for t in job_tags if t not in resume_skills]
    coverage = 0.0 if not job_tags else (len(overlap) / max(1, len(job_tags)))
    percent = int(round(coverage * 100))
    strength = f"Strong match: your {', '.join(sorted(list(overlap))[:4])} experience fits {percent}% of required skills." if percent >= 60 else \
               f"Partial match: about {percent}% of listed skills align."
    gap = None
    if missing:
        gap = "Gap: needs " + ", ".join(sorted(missing)[:4]) + " which you don’t mention."
    fairness = "Matching ignores name, gender, photo, and age — only skills, roles, and experience are used."
    notes = []
    if mode == "remote" and remote:
        notes.append("Remote-friendly role matches your preference.")
    if mode == "onsite" and not remote:
        notes.append("On-site role matches your preference.")
    if region and country_hit:
        notes.append(f"Location matches {region} preference.")
    return {
        "summary": strength,
        "gaps": missing[:8],
        "fairness": fairness,
        "notes": notes,
        "matched_skills": sorted(list(overlap))[:8],
        "title_tokens": list(_tokenize_tags_from_title(title))[:10],
    }

def rank_jobs(
    skills: List[str],
    region: Optional[str],
    roles: Optional[List[str]] = None,
    *,
    countries: Optional[List[str]] = None,
    mode: str = "any"  # "remote" | "onsite" | "any"
) -> List[Dict[str, Any]]:
    # Fetch diversified set of jobs (implementation inside all_sources),
    # then score them against the candidate profile.
    jobs = all_sources(skills or [])
    # If scraping fails or returns too few, pad with curated fallback
    if len(jobs) < 30:
        jobs = jobs + FALLBACK_JOBS

    # Normalize mode, then apply region/country + remote filter
    mode_n = _normalize_mode(mode)
    jobs = _region_country_filter(jobs, region=region, countries=countries, mode=mode_n)

    # If user requested MENA/SSA, drop any leftover jobs whose location
    # is explicitly tagged as US/EU to avoid non-local fallbacks.
    region_key = _normalize_region(region)
    if region_key in {"mena", "ssa"}:
        bad_tokens = {
            " usa", " united states", " us-", "california", "new york",
            "canada", "germany", "sweden", "latam", "latin america",
            "switzerland", " uk", " united kingdom", "australia",
            "netherlands", "france", "spain",
            # Explicitly filter Asia/Americas labels for MENA/SSA focus
            "asia", "apac", "india", "singapore", "china", "japan", "korea",
            "americas", "north america", "south america"
        }
        cleaned = []
        for j in jobs:
            loc = _lc(j.get("location"))
            if any(tok in loc for tok in bad_tokens):
                continue
            cleaned.append(j)
        jobs = cleaned

    sset = {s.lower() for s in (skills or [])}
    roles = [r.lower() for r in (roles or [])]
    ranked = []
    country_tokens = { _lc(c) for c in (countries or []) if c }
    for j in jobs:
        title = j["title"]
        title_l = title.lower()
        tags = {t.lower() for t in j.get("tags", [])}
        if not tags:
            tags = _tokenize_tags_from_title(title)

        remote = _is_remote(j)
        loc_text = _lc(j.get("location"))
        hay = " ".join([loc_text, _lc(j.get("snippet")), title_l, " ".join(tags)])
        region_hit = bool(region) and any(k in hay for k in REGION_KEYWORDS.get(_lc(region), set()))
        country_hit = bool(country_tokens) and any(k in hay for k in country_tokens)

        # Geographical priority: prefer exact country > region > others
        geo_priority = 0 if country_hit else (1 if region_hit else 2)

        # Scoring with preference bonuses
        jacc = _jaccard(sset, tags)
        title_bonus = 0.18 if any(s in title_l for s in sset) else 0.0
        role_bonus = 0.18 if any(r in title_l for r in roles) else 0.0
        loc_bonus = 0.14 if region_hit else 0.0
        remote_bonus = 0.12 if (mode_n == "remote" and remote) or (mode_n == "onsite" and not remote) else 0.0
        score = 0.56 * jacc + title_bonus + role_bonus + loc_bonus + remote_bonus

        j2 = dict(j)
        j2["score"] = round(min(1.0, score), 2)
        j2["explanation"] = _build_explanation(sset, set(tags), title, region, mode, remote, country_hit)
        j2["remote"] = remote
        j2["region_match"] = region_hit
        j2["country_match"] = country_hit
        j2["geo_priority"] = geo_priority
        ranked.append(j2)

    ranked.sort(key=lambda x: (x.get("geo_priority", 2), -x["score"]))
    # Return top ~40 diverse, scored jobs
    return ranked[:40]

def rank_from_resume(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    skills = parsed.get("skills", {}).get("hard", []) or []
    region = parsed.get("preferred_region") or parsed.get("region") or parsed.get("location") or None
    roles = parsed.get("roles") or []
    # Optional preferences
    prefs = parsed.get("preferences", {}) if isinstance(parsed.get("preferences"), dict) else {}
    countries = prefs.get("countries") or parsed.get("countries") or []
    mode = prefs.get("work_mode") or prefs.get("remote_preference") or "any"  # "remote" | "onsite" | "any"
    return rank_jobs(skills, region, roles, countries=countries, mode=mode)
